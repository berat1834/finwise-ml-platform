# -*- coding: utf-8 -*-
"""
Created on Sat Sep 14 17:12:30 2024

@author: berat
"""
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt

# Veriyi yükle
data = pd.read_csv('loan_final313.csv')

# 'issue_d' sütununu datetime formatına çevir
data['issue_d'] = pd.to_datetime(data['issue_d'], errors='coerce')

# Geçersiz tarihleri çıkar
data = data[(data['issue_d'] > '2000-01-01') & (data['issue_d'] < '2025-01-01')]

# Eksik değerleri doldur
data['interest_rate'].fillna(data['interest_rate'].median(), inplace=True)

# 'issue_d' sütununu indeks olarak ayarla
data.set_index('issue_d', inplace=True)

# Zaman serisini al ve aylık ortalama hesapla
time_series_data = data['interest_rate'].resample('M').mean()

# Zaman serisindeki boş verileri doldur
time_series_data.fillna(method='ffill', inplace=True)

time_series_data_log = np.log(time_series_data)

# Veri sayısını kontrol et
print(time_series_data.shape)

# ARIMA modelini oluştur ve eğit
model = ARIMA(time_series_data, order=(2, 1, 2))  # Parametreleri basitleştirdim
model_fit = model.fit()

# Modelin özetini al
print(model_fit.summary())

# Tahmin yapma (örneğin, 10 adım sonrasına kadar tahmin)
predictions = model_fit.predict(start=len(time_series_data), end=len(time_series_data)+24)

# Gerçek ve tahmin edilen değerleri çizdirme
plt.plot(time_series_data, label='Gerçek Değerler')
plt.plot(predictions, color='red', label='Tahminler')
plt.legend()
plt.title('ARIMA Tahminleri')
plt.show()










