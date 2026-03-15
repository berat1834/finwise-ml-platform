# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 14:38:41 2025

@author: berat
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib

"----------------------------------------------------------------"
import pickle

# Modelin eğitildiğini varsayalım (örnek bir model)
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier()
model.fit([[30, 50000, 5], [45, 80000, 10], [25, 30000, 2]], [1, 0, 1])  # Örnek veri

# Modeli kaydet
with open("kredi_risk_model.pkl", "wb") as file:
    pickle.dump(model, file)

"-----------------------------------------------------------------"

from flask import Flask, request, jsonify
import numpy as np

# Flask uygulamasını başlat
app = Flask(__name__)

# Kaydedilen modeli yükle
with open("kredi_risk_model.pkl", "rb") as file:
    model = pickle.load(file)

# API'ye veri göndermek için bir endpoint oluştur
@app.route('/tahmin', methods=['POST'])
def kredi_risk_tahmini():
    try:
        data = request.json  # Kullanıcıdan gelen JSON verisi
        
        # Girdi verilerini al
        yaş = data["yas"]
        gelir = data["gelir"]
        çalışma_yılı = data["calisma_yili"]
        
        # Modelin anlayabileceği formata çevir
        girdi = np.array([[yaş, gelir, çalışma_yılı]])
        
        # Modelden tahmin al
        tahmin = model.predict(girdi)
        
        # Tahmin sonucunu döndür
        return jsonify({"kredi_riski": int(tahmin[0])})
    
    except Exception as e:
        return jsonify({"hata": str(e)})

# Flask uygulamasını başlat
if __name__ == "__main__":
    app.run(debug=False)


"-------------------------------------------------------------------------------"

# Veri yükleme
data = pd.read_csv('credit_risk_dataset.csv')

# Eksik değerleri doldurma
data.fillna(data.median(numeric_only=True), inplace=True)

# Kategorik verileri dönüştürme (One-Hot Encoding)
data = pd.get_dummies(data, columns=['person_home_ownership', 'loan_intent', 'loan_grade', 'cb_person_default_on_file'], drop_first=True)

# Özellikler (X) ve hedef değişken (y)
X = data.drop(columns=['loan_status'])  # loan_status, tahmin edilecek sütun
y = data['loan_status']

# Eğitim ve test setine bölme
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Random Forest Modeli
model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)

# Modeli kaydetme
joblib.dump(model, 'credit_risk_model.pkl')

# Kullanıcıdan bilgi alma ve tahmin yapma fonksiyonu
def kredi_tahmin_et():
    print("Lütfen aşağıdaki bilgileri girin:")
    person_age = int(input("Yaşınızı girin: "))
    person_income = float(input("Gelirinizi girin: "))
    person_home_ownership = input("Ev sahipliği durumunuzu girin (Sahip/Kiralık): ")
    person_emp_length = int(input("İş tecrübenizi yıl olarak girin: "))
    loan_intent = input("Kredi başvuru amacını girin (Ev/Eğitim/Tatil): ")
    loan_grade = input("Kredi notunuzu girin (A/B/C/D/E): ")
    loan_amnt = float(input("Talep ettiğiniz kredi miktarını girin: "))
    loan_int_rate = float(input("Kredi faiz oranını girin: "))
    loan_percent_income = loan_amnt / person_income  # Kredi miktarının gelire oranı
    cb_person_default_on_file = int(input("Daha önce ödeme problemi yaşadınız mı? (1: Evet, 0: Hayır): "))

    # Ev sahipliği durumu için One-Hot Encoding
    person_home_ownership_Sahip = 1 if person_home_ownership.lower() == "sahip" else 0
    person_home_ownership_Kiralık = 1 if person_home_ownership.lower() == "kiralık" else 0

    # Kredi başvuru amacını One-Hot Encoding
    loan_intent_Ev = 1 if loan_intent.lower() == "ev" else 0
    loan_intent_Eğitim = 1 if loan_intent.lower() == "eğitim" else 0
    loan_intent_Tatil = 1 if loan_intent.lower() == "tatil" else 0

    # Kredi notu için One-Hot Encoding
    loan_grade_A = 1 if loan_grade.lower() == "a" else 0
    loan_grade_B = 1 if loan_grade.lower() == "b" else 0
    loan_grade_C = 1 if loan_grade.lower() == "c" else 0
    loan_grade_D = 1 if loan_grade.lower() == "d" else 0
    loan_grade_E = 1 if loan_grade.lower() == "e" else 0

    # Giriş verilerini bir DataFrame'e dönüştürme
    input_data = {
        'person_age': [person_age],
        'person_income': [person_income],
        'person_home_ownership_Sahip': [person_home_ownership_Sahip],
        'person_home_ownership_Kiralık': [person_home_ownership_Kiralık],
        'person_emp_length': [person_emp_length],
        'loan_intent_Ev': [loan_intent_Ev],
        'loan_intent_Eğitim': [loan_intent_Eğitim],
        'loan_intent_Tatil': [loan_intent_Tatil],
        'loan_grade_A': [loan_grade_A],
        'loan_grade_B': [loan_grade_B],
        'loan_grade_C': [loan_grade_C],
        'loan_grade_D': [loan_grade_D],
        'loan_grade_E': [loan_grade_E],
        'loan_amnt': [loan_amnt],
        'loan_int_rate': [loan_int_rate],
        'loan_percent_income': [loan_percent_income],
        'cb_person_default_on_file': [cb_person_default_on_file]
    }

    input_df = pd.DataFrame(input_data)

    # Modeli yükleyip tahmin yapma
    model = joblib.load('credit_risk_model.pkl')
    
    # Modelin tahmin yapabilmesi için eksik sütunları tamamlayalım
    # Eğitim sırasında kullanılan tüm sütunları tahmin verisinde de oluşturmalıyız
    missing_cols = set(X.columns) - set(input_df.columns)
    for col in missing_cols:
        input_df[col] = 0  # Eksik sütunları sıfırlarla dolduruyoruz

    # Aynı sütun sırasını korumak için
    input_df = input_df[X.columns]

    # Tahmin yapma
    prediction = model.predict(input_df)

    # Sonucu yazdırma
    if prediction[0] == 1:
        print("Kredi Onaylandı")
    else:
        print("Kredi Reddedildi")

# Kullanıcıdan veri al ve tahmin et
kredi_tahmin_et()








