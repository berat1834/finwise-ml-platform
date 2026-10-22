#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Payment Processor: Stripe integration for credit disbursement and installment management
"""
import stripe
import os
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_example_key')

class PaymentProcessor:
    """Handle credit payments, installment plans, and transaction tracking"""
    
    def __init__(self):
        self.currency = 'usd'  # Can be adjusted per region
        self.test_mode = 'test' in stripe.api_key
    
    def create_customer(self, email, name, phone=None, metadata=None):
        """Create Stripe customer for future charges"""
        customer = stripe.Customer.create(
            email=email,
            name=name,
            phone=phone,
            metadata=metadata or {}
        )
        return customer.id
    
    def create_payment_method(self, card_token):
        """Create reusable payment method from token (for installments)"""
        payment_method = stripe.PaymentMethod.create(
            type='card',
            card={'token': card_token}
        )
        return payment_method.id
    
    def disburse_credit(self, customer_id, amount_cents, description, metadata=None):
        """
        Disburse credit to customer account (one-time payment)
        Returns: payment intent or charge details
        """
        intent = stripe.PaymentIntent.create(
            customer=customer_id,
            amount=amount_cents,  # Stripe uses cents
            currency=self.currency,
            description=description,
            metadata=metadata or {},
            statement_descriptor='FinWise Kredi'
        )
        return {
            'intent_id': intent.id,
            'client_secret': intent.client_secret,
            'amount': amount_cents / 100,  # Convert back to currency units
            'status': intent.status,
            'created': intent.created
        }
    
    def create_installment_plan(self, customer_id, total_amount_cents, 
                               num_installments, payment_method_id,
                               description='FinWise Credit Installment Plan',
                               metadata=None):
        """
        Create fixed installment plan
        Calculates equal payment amounts and due dates
        """
        # Calculate per-installment amount
        monthly_amount = total_amount_cents // num_installments
        remainder = total_amount_cents % num_installments
        
        installments = []
        today = datetime.now()
        
        for i in range(num_installments):
            # Add remainder to last installment
            payment_amount = monthly_amount + (remainder if i == num_installments - 1 else 0)
            due_date = today + timedelta(days=30 * (i + 1))
            
            installments.append({
                'number': i + 1,
                'amount_cents': int(payment_amount),
                'amount_currency': payment_amount / 100,
                'due_date': due_date.isoformat(),
                'status': 'pending'
            })
        
        # Store plan (in real system: save to database)
        plan = {
            'plan_id': f'plan_{customer_id}_{int(datetime.now().timestamp())}',
            'customer_id': customer_id,
            'total_amount_cents': total_amount_cents,
            'total_amount_currency': total_amount_cents / 100,
            'num_installments': num_installments,
            'installments': installments,
            'created': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        return plan
    
    def charge_installment(self, plan_id, installment_number, payment_method_id):
        """Charge single installment payment"""
        # In production: retrieve plan from database
        # This is a simplified version
        try:
            charge = stripe.PaymentIntent.create(
                amount=10000,  # Example: $100
                currency=self.currency,
                payment_method=payment_method_id,
                customer=plan_id.split('_')[1],  # Extract customer_id
                off_session=True,
                confirm=True,
                description=f'Installment {installment_number} payment'
            )
            
            return {
                'status': 'success' if charge.status == 'succeeded' else 'pending',
                'charge_id': charge.id,
                'amount': charge.amount / 100,
                'timestamp': datetime.now().isoformat()
            }
        except stripe.error.CardError as e:
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def refund_payment(self, payment_intent_id, amount_cents=None):
        """Refund payment (full or partial)"""
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            amount=amount_cents  # None = full refund
        )
        return {
            'refund_id': refund.id,
            'status': refund.status,
            'amount': refund.amount / 100 if refund.amount else 'full',
            'created': refund.created
        }
    
    def get_payment_history(self, customer_id, limit=10):
        """Retrieve payment history for customer"""
        charges = stripe.Charge.list(customer=customer_id, limit=limit)
        return [
            {
                'charge_id': c.id,
                'amount': c.amount / 100,
                'date': datetime.fromtimestamp(c.created).isoformat(),
                'status': c.paid,
                'receipt_url': c.receipt_url
            }
            for c in charges.data
        ]
    
    def calculate_effective_rate(self, principal, monthly_payment, num_months):
        """Calculate effective interest rate from monthly payments"""
        # Simplified: APR calculation
        total_paid = monthly_payment * num_months
        interest = total_paid - principal
        annual_rate = (interest / principal / num_months) * 12 * 100
        return round(annual_rate, 2)


# Example usage
if __name__ == '__main__':
    processor = PaymentProcessor()
    
    # Create customer
    customer_id = processor.create_customer(
        email='customer@example.com',
        name='Müşteri Adı',
        metadata={'credit_id': '12345'}
    )
    print(f'✓ Customer created: {customer_id}')
    
    # Create installment plan (e.g., $5000 in 12 months)
    plan = processor.create_installment_plan(
        customer_id=customer_id,
        total_amount_cents=500000,  # $5000
        num_installments=12,
        payment_method_id='pm_example',
        description='Home improvement credit'
    )
    print(f'✓ Installment plan created:')
    print(f'  Total: ${plan["total_amount_currency"]}')
    print(f'  Monthly: ${plan["total_amount_currency"] / 12:.2f}')
    print(f'  First payment due: {plan["installments"][0]["due_date"]}')
