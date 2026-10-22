from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class FairnessService:
    """
    Centralized service for evaluating model fairness, particularly
    the ECOA 80% Rule (Disparate Impact ratio) for Q1 vs Q5 income groups.
    """
    
    MIN_DISPARATE_IMPACT_RATIO = 0.80  # Legal standard (80% rule)
    ALERT_THRESHOLD_RATIO = 0.85       # Internal proactive alert threshold

    @classmethod
    def calculate_disparate_impact(cls, q1_rate: float, q5_rate: float) -> float:
        """
        Calculate the Disparate Impact (DI) ratio between protected class (Q1)
        and reference class (Q5).
        """
        if not q5_rate or q5_rate <= 0:
            return 0.0
        
        ratio = q1_rate / q5_rate
        return float(ratio)

    @classmethod
    def check_80_percent_rule(cls, q1_rate: float, q5_rate: float) -> dict:
        """
        Evaluate if the approval rates pass the ECOA 80% rule.
        Returns a dictionary with the results.
        """
        di_ratio = cls.calculate_disparate_impact(q1_rate, q5_rate)
        passes_rule = di_ratio >= cls.MIN_DISPARATE_IMPACT_RATIO
        alert_triggered = di_ratio < cls.ALERT_THRESHOLD_RATIO

        result = {
            "di_ratio": di_ratio,
            "passes_80_rule": passes_rule,
            "alert_triggered": alert_triggered,
            "q1_rate": q1_rate,
            "q5_rate": q5_rate,
            "recommendation": ""
        }

        if alert_triggered:
            result["recommendation"] = f"Warning: DI ratio is {di_ratio:.2f}. " \
                                       "Review threshold or re-calibrate model for fairness."

        return result
