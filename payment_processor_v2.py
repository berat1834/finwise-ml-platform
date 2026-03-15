#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe Payment Processor for FinWise-ML
Production-ready payment processing with full error handling
"""
import stripe
import os
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)
stripe.api_key = os.environ.get('STRIPE_API_KEY', 'sk_test_YOUR_KEY_HERE')


class PaymentProcessor:
    """Handles all payment operations with Stripe"""
    
    def __init__(self):
        self.stripe_key = stripe.api_key
        self.webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        self.currency = 'try'  # Turkish Lira
    
    
    def create_customer(self, email, name, phone=None, metadata=None):
        """Create Stripe customer
        
        Args:
            email: Customer email
            name: Customer full name
            phone: Optional phone number
            metadata: Optional metadata dict
            
        Returns:
            Stripe customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                phone=phone or '',
                metadata=metadata or {},
                description=f'FinWise Customer: {name}'
            )
            logger.info(f'✓ Stripe customer created: {customer.id}')
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name
            }
        except stripe.error.CardError as e:
            logger.error(f'Card error: {e.user_message}')
            raise Exception(f'Card error: {e.user_message}')
        except stripe.error.RateLimitError:
            logger.error('Rate limit error')
            raise Exception('Rate limit reached, please try again later')
        except stripe.error.InvalidRequestError as e:
            logger.error(f'Invalid request: {e.message}')
            raise Exception(f'Invalid request: {e.message}')
        except stripe.error.StripeError as e:
            logger.error(f'Stripe error: {str(e)}')
            raise Exception(f'Payment processor error: {str(e)}')
    
    
    def create_installment_plan(self, customer_id, amount, months, metadata=None):
        """Create monthly installment subscription
        
        Args:
            customer_id: Stripe customer ID
            amount: Monthly payment amount (in currency units)
            months: Number of months
            metadata: Optional metadata
            
        Returns:
            Subscription object with plan details
        """
        try:
            # Create product
            product = stripe.Product.create(
                name='FinWise Credit Installment',
                type='service',
                metadata={'finwise': 'installment'}
            )
            
            # Create recurring price
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(amount * 100),  # Amount in cents
                currency=self.currency,
                recurring={
                    'interval': 'month',
                    'interval_count': 1
                }
            )
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price.id}],
                payment_behavior='error_if_incomplete',
                metadata=metadata or {'finwise': 'true'},
                billing_cycle_anchor=datetime.utcnow().replace(day=1).timestamp()
            )
            
            logger.info(f'✓ Subscription created: {subscription.id}')
            return {
                'id': subscription.id,
                'customer_id': customer_id,
                'monthly_amount': amount,
                'months': months,
                'total_amount': amount * months,
                'status': subscription.status,
                'start_date': datetime.fromtimestamp(subscription.created).isoformat()
            }
        except stripe.error.StripeError as e:
            logger.error(f'Subscription creation error: {str(e)}')
            raise Exception(f'Failed to create subscription: {str(e)}')
    
    
    def charge_installment(self, customer_id, amount, description=''):
        """Charge single installment
        
        Args:
            customer_id: Stripe customer ID
            amount: Amount to charge
            description: Charge description
            
        Returns:
            Charge object
        """
        try:
            charge = stripe.Charge.create(
                amount=int(amount * 100),
                currency=self.currency,
                customer=customer_id,
                description=description,
                metadata={'finwise': 'true'}
            )
            logger.info(f'✓ Charge succeeded: {charge.id}')
            return {
                'id': charge.id,
                'amount': amount,
                'status': charge.status,
                'receipt_url': charge.receipt_url
            }
        except stripe.error.CardError as e:
            logger.error(f'Card declined: {e.user_message}')
            raise Exception(f'Card declined: {e.user_message}')
        except stripe.error.StripeError as e:
            logger.error(f'Charge error: {str(e)}')
            raise Exception(f'Charge failed: {str(e)}')
    
    
    def refund_payment(self, charge_id, amount=None):
        """Refund payment
        
        Args:
            charge_id: Original charge ID
            amount: Partial refund amount (full if None)
            
        Returns:
            Refund object
        """
        try:
            refund = stripe.Refund.create(
                charge=charge_id,
                amount=int(amount * 100) if amount else None,
                metadata={'finwise': 'true'}
            )
            logger.info(f'✓ Refund created: {refund.id}')
            return {
                'id': refund.id,
                'charge_id': charge_id,
                'amount': refund.amount / 100,
                'status': refund.status
            }
        except stripe.error.StripeError as e:
            logger.error(f'Refund error: {str(e)}')
            raise Exception(f'Refund failed: {str(e)}')
    
    
    def get_payment_history(self, customer_id, limit=10):
        """Get customer payment history
        
        Args:
            customer_id: Stripe customer ID
            limit: Number of records to retrieve
            
        Returns:
            List of charge objects
        """
        try:
            charges = stripe.Charge.list(
                customer=customer_id,
                limit=limit,
                expand=['data.balance_transaction']
            )
            
            return [{
                'id': charge.id,
                'amount': charge.amount / 100,
                'currency': charge.currency,
                'status': charge.status,
                'description': charge.description,
                'created': datetime.fromtimestamp(charge.created).isoformat(),
                'receipt_url': charge.receipt_url
            } for charge in charges.data]
        except stripe.error.StripeError as e:
            logger.error(f'History fetch error: {str(e)}')
            raise Exception(f'Failed to fetch payment history: {str(e)}')
    
    
    def get_invoice(self, invoice_id):
        """Get invoice details
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            Invoice object
        """
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return {
                'id': invoice.id,
                'amount_due': invoice.amount_due / 100,
                'amount_paid': invoice.amount_paid / 100,
                'status': invoice.status,
                'due_date': datetime.fromtimestamp(invoice.due_date).isoformat() if invoice.due_date else None,
                'pdf_url': invoice.invoice_pdf
            }
        except stripe.error.StripeError as e:
            logger.error(f'Invoice fetch error: {str(e)}')
            raise Exception(f'Failed to fetch invoice: {str(e)}')
    
    
    def calculate_effective_rate(self, monthly_payment, principal, months):
        """Calculate effective annual rate (APR)
        
        Args:
            monthly_payment: Monthly payment amount
            principal: Original loan amount
            months: Loan term in months
            
        Returns:
            Annual percentage rate (0.12 = 12%)
        """
        # Newton-Raphson method for finding rate
        rate = 0.01  # Starting guess
        for _ in range(100):
            # PV formula: sum of discounted payments
            pv = sum([monthly_payment / (1 + rate/12)**(i+1) for i in range(months)])
            if abs(pv - principal) < 0.01:
                return rate
            
            # Derivative for Newton-Raphson
            dpv = sum([-(i+1) * monthly_payment / (12 * (1 + rate/12)**(i+2)) for i in range(months)])
            rate = rate - (pv - principal) / dpv
        
        return rate
    
    
    def calculate_installment(self, principal, annual_rate, months):
        """Calculate monthly installment using amortization formula
        
        Args:
            principal: Loan amount
            annual_rate: Annual interest rate (0.12 = 12%)
            months: Loan term in months
            
        Returns:
            Monthly payment amount
        """
        monthly_rate = annual_rate / 12
        
        if monthly_rate == 0:
            return principal / months
        
        # Amortization formula
        numerator = monthly_rate * (1 + monthly_rate) ** months
        denominator = (1 + monthly_rate) ** months - 1
        payment = principal * (numerator / denominator)
        
        return round(payment, 2)
    
    
    def validate_card(self, token):
        """Validate card token
        
        Args:
            token: Stripe token or payment method ID
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # This would be used in tokenization flow
            token_obj = stripe.Token.retrieve(token)
            return token_obj.card.fingerprint is not None
        except stripe.error.StripeError:
            return False
    
    
    def create_payment_intent(self, customer_id, amount, metadata=None):
        """Create payment intent for advanced payment flows
        
        Args:
            customer_id: Stripe customer ID
            amount: Payment amount
            metadata: Optional metadata
            
        Returns:
            Payment intent object
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=self.currency,
                customer=customer_id,
                metadata=metadata or {'finwise': 'true'},
                payment_method_types=['card']
            )
            return {
                'id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount,
                'status': intent.status
            }
        except stripe.error.StripeError as e:
            logger.error(f'Payment intent error: {str(e)}')
            raise Exception(f'Failed to create payment intent: {str(e)}')
    
    
    def log_transaction(self, transaction_data):
        """Log transaction for audit trail
        
        Args:
            transaction_data: Dict with transaction details
            
        Returns:
            Log entry
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'transaction': transaction_data
        }
        logger.info(f'Transaction log: {json.dumps(log_entry)}')
        return log_entry


if __name__ == '__main__':
    processor = PaymentProcessor()
    print('✓ Payment processor initialized')
