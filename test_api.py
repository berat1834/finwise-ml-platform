# -*- coding: utf-8 -*-
"""
Test client - API endpoint testi
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_health():
    print("\n1. Health Check...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
    return resp.status_code == 200

def test_prediction():
    print("\n2. Credit Decision Test...")
    payload = {
        "person_age": 30,
        "person_income": 60000,
        "person_emp_length": 5,
        "loan_amnt": 12000,
        "loan_int_rate": 7.5,
        "loan_percent_income": 0.2,
        "cb_person_cred_hist_length": 8,
        "person_home_ownership": "RENT",
        "loan_intent": "PERSONAL",
        "loan_grade": "B",
        "cb_person_default_on_file": "N"
    }
    resp = requests.post(f"{BASE_URL}/degerlendir", json=payload)
    print(f"   Status: {resp.status_code}")
    result = resp.json()
    print(f"   Karar: {result['tahmin']}")
    print(f"   Onay Olasılığı: {result['onay_olasiligi']:.2%}")
    print(f"   Red Olasılığı: {result['red_olasiligi']:.2%}")
    print(f"   Threshold: {result['threshold']:.3f}")
    return resp.status_code == 200

def test_explanation():
    print("\n3. Explanation Test (SHAP)...")
    payload = {
        "person_age": 30,
        "person_income": 60000,
        "person_emp_length": 5,
        "loan_amnt": 12000,
        "loan_int_rate": 7.5,
        "loan_percent_income": 0.2,
        "cb_person_cred_hist_length": 8,
        "person_home_ownership": "RENT",
        "loan_intent": "PERSONAL",
        "loan_grade": "B",
        "cb_person_default_on_file": "N"
    }
    resp = requests.post(f"{BASE_URL}/explain", json=payload)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"   Top 5 Features:")
        for feat in result['top_features'][:5]:
            print(f"      • {feat['feature']}: {feat['contribution']:.4f}")
    return resp.status_code == 200

def test_stats():
    print("\n4. Model Statistics...")
    resp = requests.get(f"{BASE_URL}/istatistik")
    print(f"   Status: {resp.status_code}")
    result = resp.json()
    print(f"   Model: {result.get('model_tipi')}")
    print(f"   Threshold: {result.get('threshold')}")
    if result.get('meta'):
        metrics = result['meta'].get('metrics', {})
        print(f"   ROC AUC: {metrics.get('roc_auc', 'N/A'):.3f}")
        print(f"   Accuracy: {metrics.get('accuracy', 'N/A'):.3f}")
    return resp.status_code == 200

if __name__ == '__main__':
    print("="*60)
    print("KREDİ RİSK SİSTEMİ - API TEST")
    print("="*60)
    
    try:
        results = []
        results.append(("Health Check", test_health()))
        results.append(("Prediction", test_prediction()))
        results.append(("Explanation", test_explanation()))
        results.append(("Statistics", test_stats()))
        
        print("\n" + "="*60)
        print("TEST SONUÇLARI")
        print("="*60)
        for name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status:8} | {name}")
        
        all_passed = all(p for _, p in results)
        if all_passed:
            print("\n🎉 Tüm testler başarılı!")
        else:
            print("\n⚠ Bazı testler başarısız!")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ HATA: API'ye bağlanılamıyor!")
        print("Lütfen sunucuyu başlatın: python run_production.py")
        print("="*60 + "\n")
