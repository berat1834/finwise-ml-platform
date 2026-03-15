import pandas as pd

df = pd.read_csv('credit_risk_dataset.csv')
print(f'Toplam kayıt: {len(df)}')
print(f'Özellik sayısı: {df.shape[1]}')
print(f'\nSütunlar:')
print(df.columns.tolist())
print(f'\nHedef değişken dağılımı:')
print(df["loan_status"].value_counts())
print(f'\nTemel istatistikler:')
print(df.describe())
