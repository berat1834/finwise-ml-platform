import random

class FraudService:
    """
    Centralized service for evaluating credit application fraud risk.
    Simulates checks against official data sources (e.g. Findeks/KKB, Open Banking).
    """

    @classmethod
    def evaluate(cls, data: dict) -> dict:
        """
        Evaluates the input data against fraud rules and mock official APIs.
        Returns a dictionary with fraud analysis results.
        """
        is_fraud = False
        fraud_score = 0
        reasons = []

        try:
            person_age = int(data.get("person_age", 0))
            person_emp_length = int(data.get("person_emp_length", 0))
            person_income = float(data.get("person_income", 0.0))
            loan_percent_income = float(data.get("loan_percent_income", 0.0))
        except (ValueError, TypeError):
            return {
                "is_fraud": True,
                "score": 100,
                "reasons": ["Veri formatı manipülasyonu tespit edildi."]
            }

        # Rule 1: Age vs Employment Length Anomaly
        # You cannot have worked longer than (Age - 18) years realistically
        if person_age - person_emp_length < 18:
            is_fraud = True
            fraud_score += 80
            reasons.append(f"İstihdam Anomalisi: {person_age} yaşındaki birinin {person_emp_length} yıl çalışma geçmişi olamaz.")

        # Rule 2: Extreme Loan Percent Income without property
        # Trying to borrow > 80% of income while renting
        home_ownership = data.get("person_home_ownership", "").upper()
        if loan_percent_income > 0.8 and home_ownership == "RENT":
            is_fraud = True
            fraud_score += 60
            reasons.append("Riskli Borçlanma Anomalisi: Yüksek kira gideri riski varken aşırı oranda borçlanma talebi.")

        # Rule 3: Official Data Mock (Simulating Open Banking check)
        # We probabilistically simulate that 15% of users exaggerated their income >30%
        # We use a deterministic seed based on income and age to keep the simulation stable per identical request
        random.seed(person_age + int(person_income))
        mock_api_check = random.random()
        
        if mock_api_check < 0.15: # 15% chance to hit the mock mismatch rule
            official_income = person_income * 0.6  # System finds out they only make 60% of what they claimed
            is_fraud = True
            fraud_score += 90
            reasons.append(f"Açık Bankacılık Uyuşmazlığı: Beyan edilen gelir ({person_income} TL) ile SGK/Banka kayıtları ({official_income} TL) uyuşmuyor.")

        # Cap score at 100
        fraud_score = min(fraud_score, 100)
        
        # If score is > 70, we flag it as critical fraud
        if fraud_score >= 70:
            is_fraud = True

        return {
            "is_fraud": is_fraud,
            "score": fraud_score,
            "reasons": reasons
        }
