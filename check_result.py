#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kredi başvuru sonucunu kontrol eden script
"""
from app import app, KrediRiskModel
import json

# Model'i yükle
model = KrediRiskModel()

# Örnek başvuru - SİZİN GİRDİĞİNİZ DEĞERLERİ BURAYA YAZIN
test_data = {
    'person_age': 25,
    'person_income': 25000,
    'person_emp_length': 1,
    'loan_amnt': 15000,
    'loan_int_rate': 5.0,
    'loan_percent_income': 15000 / 25000,  # 0.6
    'cb_person_cred_hist_length': 1,
    'person_home_ownership': 'RENT',
    'loan_intent': 'VENTURE',
    'loan_grade': 'C',
    'cb_person_default_on_file': 'N'
}

print("="*60)
print("KREDİ BAŞVURU SONUCU KONTROLÜ")
print("="*60)

# Girilen değerleri göster
print("\n📋 Başvuru Bilgileri:")
print(f"  Yaş: {test_data['person_age']}")
print(f"  Gelir: ${test_data['person_income']:,}")
print(f"  Çalışma Süresi: {test_data['person_emp_length']} yıl")
print(f"  Kredi Miktarı: ${test_data['loan_amnt']:,}")
print(f"  Faiz Oranı: {test_data['loan_int_rate']}%")
print(f"  Gelir/Kredi Oranı: {test_data['loan_percent_income']:.2%}")
print(f"  Kredi Geçmişi: {test_data['cb_person_cred_hist_length']} yıl")
print(f"  Ev Durumu: {test_data['person_home_ownership']}")
print(f"  Kredi Amacı: {test_data['loan_intent']}")
print(f"  Kredi Notu: {test_data['loan_grade']}")
print(f"  Eski Temerrüt: {test_data['cb_person_default_on_file']}")

# Tahmin yap
result = model.tahmin_yap(test_data)

print("\n" + "="*60)
print("🎯 MODEL KARARI")
print("="*60)
print(f"Karar: {result['tahmin']}")
print(f"Onay Olasılığı: {result['onay_olasiligi']:.2%}")
print(f"Red Olasılığı: {result['red_olasiligi']:.2%}")
print(f"Kullanılan Eşik: {result['threshold']:.3f}")

# SHAP açıklama
print("\n" + "="*60)
print("💡 KARARI ETKİLEYEN EN ÖNEMLİ FAKTÖRLER (SHAP)")
print("="*60)
explanation = model.explain(test_data, top_n=10)
print(f"\n{'Faktör':<35} {'Katkı':>10} {'Yön'}")
print("-"*60)
for feat in explanation:  # explanation is already a list
    contribution = feat['contribution']
    direction = "🔴 RED" if contribution > 0 else "🟢 ONAY"
    print(f"{feat['feature']:<35} {contribution:>10.4f}  {direction}")

# Sonuç analizi
print("\n" + "="*60)
print("📊 SONUÇ ANALİZİ")
print("="*60)

if result['tahmin'] == 'ONAYLANDI':
    print("✅ Başvuru ONAYLANDI")
    print(f"   Model, bu müşterinin kredisini geri ödeyeceğine %{result['onay_olasiligi']*100:.1f} güveniyor.")
else:
    print("❌ Başvuru REDDEDİLDİ")
    print(f"   Model, bu müşterinin temerrüde düşme riski %{result['red_olasiligi']*100:.1f}.")

print("\n🔍 Kritik Faktörler:")
top_3 = explanation[:3]  # explanation is already a list
for i, feat in enumerate(top_3, 1):
    if feat['contribution'] > 0:
        print(f"  {i}. {feat['feature']}: RED riskini artırıyor (+{feat['contribution']:.4f})")
    else:
        print(f"  {i}. {feat['feature']}: ONAY şansını artırıyor ({feat['contribution']:.4f})")

print("\n" + "="*60)
print("✓ Analiz tamamlandı!")
print("="*60)
