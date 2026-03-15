#!/usr/bin/env python3
"""
GATE 2: Model Routing Logic Validation
Tests single, shadow, and canary modes
"""

import requests
import time
import json
import statistics
from collections import Counter

API_URL = "http://127.0.0.1:5000"

def get_auth_token():
    """Get JWT token"""
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=5
    )
    return response.json()["access_token"]

def make_prediction(token, age, income):
    """Make a prediction and return response + latency"""
    data = {
        "person_age": age,
        "person_income": income,
        "person_emp_length": 5,
        "loan_amnt": 20000,
        "loan_int_rate": 10.5,
        "loan_percent_income": 30.0,
        "cb_person_cred_hist_length": 5,
        "person_home_ownership": "RENT",
        "loan_intent": "PERSONAL",
        "loan_grade": "B",
        "cb_person_default_on_file": "N"
    }
    
    start = time.time()
    response = requests.post(
        f"{API_URL}/degerlendir",
        headers={"Authorization": f"Bearer {token}"},
        json=data,
        timeout=10
    )
    latency_ms = (time.time() - start) * 1000
    
    return response.json(), latency_ms

def test_routing_mode(mode_name, num_predictions=20):
    """Test a routing mode"""
    print(f"\n{'='*60}")
    print(f"Testing: {mode_name}")
    print(f"{'='*60}")
    
    # Get health check
    health = requests.get(f"{API_URL}/health").json()
    print(f"Current Mode: {health.get('routing_mode')}")
    print(f"Canary Loaded: {health.get('canary_loaded')}")
    
    # Get token
    token = get_auth_token()
    
    # Run predictions
    results = []
    latencies = []
    models_used = []
    shadow_count = 0
    
    print(f"\nRunning {num_predictions} predictions...")
    for i in range(1, num_predictions + 1):
        try:
            response, latency = make_prediction(token, 30 + i, 60000 + i * 500)
            
            results.append(response)
            latencies.append(latency)
            
            served_by = response.get("model_routing", {}).get("served_by", "unknown")
            models_used.append(served_by)
            
            # DEBUG: Print first few responses
            if i <= 3:
                print(f"  DEBUG Pred {i}: served_by={served_by}, keys={list(response.keys())}")
            
            if response.get("model_routing", {}).get("shadow_comparison"):
                shadow_count += 1
            
            if i % 10 == 0:
                print(f"  Progress: {i}/{num_predictions}")
        except Exception as e:
            print(f"  ERROR Pred {i}: {e}")
            models_used.append("error")
    
    # Analysis
    print(f"\nResults:")
    print(f"  Predictions: {num_predictions}")
    print(f"  Avg Latency: {statistics.mean(latencies):.1f}ms")
    print(f"  P50 Latency: {statistics.median(latencies):.1f}ms")
    print(f"  P95 Latency: {sorted(latencies)[int(num_predictions * 0.95)]:.1f}ms")
    
    model_counts = Counter(models_used)
    print(f"\nModel Distribution:")
    for model, count in model_counts.items():
        pct = count / num_predictions * 100
        print(f"  {model}: {count}/{num_predictions} ({pct:.1f}%)")
    
    if shadow_count > 0:
        print(f"\nShadow Scoring: {shadow_count}/{num_predictions} ({shadow_count/num_predictions*100:.1f}%)")
    
    return {
        "mode": mode_name,
        "predictions": num_predictions,
        "avg_latency_ms": statistics.mean(latencies),
        "p95_latency_ms": sorted(latencies)[int(num_predictions * 0.95)],
        "model_distribution": dict(model_counts),
        "shadow_count": shadow_count,
        "latencies": latencies
    }

def main():
    """Main test runner"""
    print("="*60)
    print("GATE 2: MODEL ROUTING LOGIC VALIDATION")
    print("="*60)
    
    # Check API health
    try:
        health = requests.get(f"{API_URL}/health", timeout=3).json()
        print(f"\nAPI Status: {health.get('status')}")
        current_mode = health.get('routing_mode')
        print(f"Current Routing Mode: {current_mode}")
    except Exception as e:
        print(f"\nERROR: API not responding - {e}")
        return
    
    # Test current mode
    result = test_routing_mode(current_mode, num_predictions=30)
    
    # Save results
    with open("gate2_current_mode_results.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n{'='*60}")
    print("GATE 2 Test Complete")
    print(f"{'='*60}")
    print(f"\nCurrent mode ({current_mode}) tested with 30 predictions.")
    print(f"Results saved to: gate2_current_mode_results.json")
    
    # Validation
    if current_mode == "single":
        primary_pct = result["model_distribution"].get("primary", 0) / result["predictions"] * 100
        if primary_pct == 100:
            print(f"\n✓ SINGLE MODE: PASSED (100% primary)")
        else:
            print(f"\n✗ SINGLE MODE: FAILED ({primary_pct}% primary, expected 100%)")
    
    elif current_mode == "shadow":
        primary_pct = result["model_distribution"].get("primary", 0) / result["predictions"] * 100
        shadow_pct = result["shadow_count"] / result["predictions"] * 100
        if primary_pct == 100 and shadow_pct >= 95:
            print(f"\n✓ SHADOW MODE: PASSED (100% primary served, {shadow_pct:.1f}% shadow scored)")
        else:
            print(f"\n✗ SHADOW MODE: FAILED (primary: {primary_pct}%, shadow: {shadow_pct:.1f}%)")
    
    elif current_mode == "canary":
        canary_pct = result["model_distribution"].get("fair_v2", 0) / result["predictions"] * 100
        if 5 <= canary_pct <= 15:
            print(f"\n✓ CANARY MODE: PASSED ({canary_pct:.1f}% canary, target 10% +/- 5%)")
        else:
            print(f"\n✗ CANARY MODE: FAILED ({canary_pct:.1f}% canary, expected 5-15%)")
    
    print(f"\nTo test other modes:")
    print(f"  1. Update .env: MODEL_ROUTING_MODE=single|shadow|canary")
    print(f"  2. Restart API: Ctrl+C in API terminal, then python app_v2_secure.py")
    print(f"  3. Run: python test_gate2.py")

if __name__ == "__main__":
    main()
