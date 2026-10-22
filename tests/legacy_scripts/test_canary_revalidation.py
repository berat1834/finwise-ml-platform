#!/usr/bin/env python3
"""
GATE 2 Canary Mode Revalidation Script
=====================================

Purpose: Validate that the route_key UUID fix results in proper canary traffic split
(Expected: 5-15% of requests served by canary_fair_v2 model)

This script:
1. Generates 150 diverse synthetic credit applications
2. Submits predictions with per-request UUID-based route_key values
3. Tracks which model (primary vs canary) served each request
4. Calculates actual traffic split percentage
5. Queries Prometheus metrics for confirmation

Date: March 6, 2026
Author: FinWise QA Team
"""

import requests
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime

# Configuration
API_BASE_URL = "http://127.0.0.1:5000"
CANARY_MODE = "canary"
PROMETHEUS_URL = "http://127.0.0.1:9090"

# Test data: 150 diverse synthetic applicants
def generate_test_applications(count=150):
    """Generate realistic credit application test data with income diversity."""
    apps = []
    income_groups = [
        {"base": 10000, "range": 5000},   # Q1: Very Low (10K-15K)
        {"base": 25000, "range": 10000},  # Q2: Low (25K-35K)
        {"base": 50000, "range": 15000},  # Q3: Middle (50K-65K)
        {"base": 80000, "range": 20000},  # Q4: High (80K-100K)
        {"base": 150000, "range": 50000}, # Q5: Very High (150K-200K)
    ]
    
    for i in range(count):
        income_group = income_groups[i % len(income_groups)]
        income = income_group["base"] + (i % income_group["range"])
        
        app = {
            "application_id": f"TEST_GATE2_REVAL_{i:04d}",
            "age": 25 + (i % 40),
            "employment_months": 12 + (i % 300),
            "income": income,
            "loan_amount": income * (0.3 + (i % 20) / 100),
            "credit_score": 300 + (i % 500),
            "existing_loans": i % 5,
            "education": ["high_school", "bachelor", "master"][i % 3],
            "monthly_debt": income * (0.1 + (i % 30) / 100),
        }
        apps.append(app)
    
    return apps


def submit_predictions(applications, mode=CANARY_MODE):
    """Submit applications to API and track routing decisions."""
    # First, get JWT token
    print("Authenticating with API...")
    try:
        login_response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": "test_user", "password": "test_password"},
            timeout=5
        )
        if login_response.status_code != 200:
            print(f"✗ Authentication failed: {login_response.status_code}")
            return None
        
        jwt_token = login_response.json().get("access_token")
        if not jwt_token:
            print("✗ No JWT token in auth response")
            return None
        
        print(f"✓ JWT token obtained")
    except Exception as e:
        print(f"✗ Auth error: {e}")
        return None
    
    results = {
        "total_submissions": 0,
        "successful": 0,
        "failed": 0,
        "routing_decisions": defaultdict(int),
        "predictions": [],
        "errors": [],
    }
    
    print(f"\n{'='*70}")
    print(f"Submitting {len(applications)} predictions in {mode} mode")
    print(f"Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    for idx, app in enumerate(applications):
        results["total_submissions"] += 1
        
        try:
            # Each request gets a unique route_key with per-request UUID
            # This ensures canary traffic split works properly
            unique_route_key = f"{app['application_id']}_{uuid.uuid4().hex[:8]}"
            
            payload = {
                "application_id": app["application_id"],
                "age": app["age"],
                "employment_months": app["employment_months"],
                "income": app["income"],
                "loan_amount": app["loan_amount"],
                "credit_score": app["credit_score"],
                "existing_loans": app["existing_loans"],
                "education": app["education"],
                "monthly_debt": app["monthly_debt"],
                # Pass route_key as header for proper bucketing
                # (In production, this comes from current_user_id + uuid)
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Debug-Route-Key": unique_route_key,  # For debugging
            }
            
            response = requests.post(
                f"{API_BASE_URL}/degerlendir",
                json=payload,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                decision = response.json()
                results["successful"] += 1
                
                # Extract routing information
                served_by = decision.get("model_routing", {}).get("served_by", "unknown")
                routing_mode = decision.get("model_routing", {}).get("mode", "unknown")
                
                results["routing_decisions"][served_by] += 1
                results["predictions"].append({
                    "app_id": app["application_id"],
                    "served_by": served_by,
                    "routing_mode": routing_mode,
                    "decision": decision.get("final_decision"),
                    "approval_prob": decision.get("approval_probability"),
                    "income": app["income"],
                })
                
                # Progress indicator
                if (idx + 1) % 25 == 0:
                    elapsed = time.time() - start_time
                    rate = (idx + 1) / elapsed
                    eta_remaining = (len(applications) - (idx + 1)) / rate
                    print(f"  [{idx + 1:3d}/{len(applications)}] "
                          f"Served: {served_by:30s} | "
                          f"Rate: {rate:.1f} req/s | "
                          f"ETA: {eta_remaining:.0f}s")
            else:
                results["failed"] += 1
                results["errors"].append({
                    "app_id": app["application_id"],
                    "status_code": response.status_code,
                    "error": response.text[:100],
                })
                print(f"  ERROR [{idx + 1}]: Status {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            results["failed"] += 1
            results["errors"].append({
                "app_id": app["application_id"],
                "error": str(e)[:100],
            })
            print(f"  EXCEPTION [{idx + 1}]: {str(e)[:50]}")
    
    elapsed_time = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"Submission Complete")
    print(f"Total Time: {elapsed_time:.1f}s | Avg Rate: {len(applications)/elapsed_time:.1f} req/s")
    print(f"{'='*70}\n")
    
    return results


def analyze_canary_split(results):
    """Analyze canary vs primary traffic split."""
    print(f"\n{'='*70}")
    print("CANARY TRAFFIC SPLIT ANALYSIS")
    print(f"{'='*70}\n")
    
    print(f"Total Submissions: {results['total_submissions']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['successful']/results['total_submissions']*100:.1f}%")
    
    print(f"\n{'Routing Decision':<35} {'Count':<10} {'Percentage':<12}")
    print(f"{'-'*57}")
    
    routing_counts = results["routing_decisions"]
    for route, count in sorted(routing_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / results["successful"] * 100
        print(f"{route:<35} {count:<10} {percentage:>6.2f}%")
    
    # Calculate canary split
    canary_count = routing_counts.get("canary_fair_v2_served", 0)
    canary_percentage = canary_count / results["successful"] * 100 if results["successful"] > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"CANARY SPLIT RESULT: {canary_percentage:.2f}%")
    print(f"{'='*70}")
    
    # Validation
    expected_min = 5.0
    expected_max = 15.0
    
    print(f"\nExpected Range: {expected_min}% - {expected_max}%")
    print(f"Actual: {canary_percentage:.2f}%")
    
    if expected_min <= canary_percentage <= expected_max:
        print("✓ CANARY SPLIT WITHIN EXPECTED RANGE - VALIDATION PASS")
        return True
    else:
        print("✗ CANARY SPLIT OUTSIDE EXPECTED RANGE - VALIDATION FAIL")
        return False


def query_prometheus_metrics():
    """Query Prometheus metrics to confirm canary routing counters."""
    print(f"\n{'='*70}")
    print("PROMETHEUS METRICS CONFIRMATION")
    print(f"{'='*70}\n")
    
    try:
        # Query canary traffic metric
        query = 'sum(finwise_model_route_total{route="canary_fair_v2_served"}) / sum(finwise_model_route_total)'
        params = {"query": query}
        
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params=params,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data", {}).get("result"):
                value = float(data["data"]["result"][0]["value"][1])
                percentage = value * 100
                print(f"Prometheus canary_fair_v2_served ratio: {percentage:.2f}%")
                return percentage
        else:
            print(f"Prometheus query failed: {response.status_code}")
    except Exception as e:
        print(f"Could not query Prometheus: {e}")
    
    return None


def print_summary_by_income(results):
    """Show canary vs primary split by income quintile."""
    print(f"\n{'='*70}")
    print("CANARY SPLIT BY INCOME QUINTILE (FAIRNESS CHECK)")
    print(f"{'='*70}\n")
    
    # Group by income quintiles
    quintiles = {
        "Q1 (Lowest)": [],
        "Q2": [],
        "Q3 (Middle)": [],
        "Q4": [],
        "Q5 (Highest)": [],
    }
    
    for pred in results["predictions"]:
        income = pred["income"]
        if income <= 15000:
            key = "Q1 (Lowest)"
        elif income <= 35000:
            key = "Q2"
        elif income <= 65000:
            key = "Q3 (Middle)"
        elif income <= 100000:
            key = "Q4"
        else:
            key = "Q5 (Highest)"
        
        quintiles[key].append(pred)
    
    print(f"{'Income Quintile':<20} {'Count':<10} {'Canary %':<12} {'Primary %':<12}")
    print(f"{'-'*54}")
    
    for q_name, predictions in quintiles.items():
        if not predictions:
            continue
        
        canary_count = sum(1 for p in predictions if "canary" in p["served_by"])
        primary_count = len(predictions) - canary_count
        
        canary_pct = canary_count / len(predictions) * 100 if predictions else 0
        primary_pct = primary_count / len(predictions) * 100 if predictions else 0
        
        print(f"{q_name:<20} {len(predictions):<10} {canary_pct:>6.2f}%      {primary_pct:>6.2f}%")


def save_detailed_results(results):
    """Save detailed results to JSON for analysis."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "test_name": "GATE_2_CANARY_REVALIDATION",
        "summary": {
            "total_submissions": results["total_submissions"],
            "successful": results["successful"],
            "failed": results["failed"],
            "routing_distribution": dict(results["routing_decisions"]),
        },
        "predictions": results["predictions"],
    }
    
    filename = f"GATE_2_CANARY_REVALIDATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nDetailed results saved to: {filename}")
    return filename


def main():
    """Run complete canary validation test."""
    print("\n" + "="*70)
    print("GATE 2: CANARY MODE REVALIDATION TEST")
    print("="*70)
    print("Testing route_key UUID fix for proper canary traffic split")
    print("="*70)
    
    try:
        # Step 1: Generate test data
        print("\n[1/5] Generating 150 diverse test applications...")
        applications = generate_test_applications(count=150)
        print(f"      Generated {len(applications)} applications across 5 income quintiles")
        
        # Step 2: Submit predictions
        print("\n[2/5] Submitting predictions to API...")
        results = submit_predictions(applications, mode=CANARY_MODE)
        
        # Step 3: Analyze local results
        print("\n[3/5] Analyzing routing decisions...")
        canary_valid = analyze_canary_split(results)
        
        # Step 4: Check Prometheus metrics
        print("\n[4/5] Querying Prometheus metrics...")
        prometheus_value = query_prometheus_metrics()
        
        # Step 5: Detailed analysis
        print("\n[5/5] Generating detailed analysis...")
        print_summary_by_income(results)
        
        # Save results
        print("\n[6/5] Saving detailed results...")
        results_file = save_detailed_results(results)
        
        # Final verdict
        print(f"\n{'='*70}")
        print("FINAL VERDICT")
        print(f"{'='*70}")
        
        if results["successful"] > 0:
            local_canary_pct = results["routing_decisions"].get("canary_fair_v2_served", 0) / results["successful"] * 100
            print(f"Local analysis: {local_canary_pct:.2f}% canary traffic")
            
            if prometheus_value is not None:
                print(f"Prometheus metrics: {prometheus_value:.2f}% canary traffic")
        
        if canary_valid:
            print("\n✓ GATE 2 CANARY REVALIDATION: PASS")
            print("  Canary traffic split is within expected 5-15% range")
            print("  Route_key UUID fix validated successfully")
        else:
            print("\n✗ GATE 2 CANARY REVALIDATION: FAIL")
            print("  Canary traffic split is outside expected range")
            print("  Further investigation required")
        
        print(f"{'='*70}\n")
        
        return results_file
    
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results_file = main()
