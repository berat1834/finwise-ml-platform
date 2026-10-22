# -*- coding: utf-8 -*-
"""
Created on Sat Sep 14 17:12:30 2024

@author: berat
"""
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
import pickle

# Modelin eğitildiğini varsayalım (örnek bir model)
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier()
model.fit([[30, 50000, 5], [45, 80000, 10], [25, 30000, 2]], [1, 0, 1])  # Örnek veri

# Modeli kaydet
with open("kredi_risk_model.pkl", "wb") as file:
    pickle.dump(model, file)



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

# Tahmin yapma
y_pred = model.predict(X_test)

# Modelin performansını değerlendirme
print("Doğruluk Skoru:", accuracy_score(y_test, y_pred))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Grafikleri oluşturma
plt.figure(figsize=(15, 10))

# 1. Confusion Matrix Heatmap
plt.subplot(2, 3, 1)
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
plt.title('Confusion Matrix')
plt.ylabel('Gerçek Değer')
plt.xlabel('Tahmin Edilen Değer')

# 2. Feature Importance
plt.subplot(2, 3, 2)
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False).head(10)
plt.barh(feature_importance['feature'], feature_importance['importance'])
plt.xlabel('Önem Derecesi')
plt.title('En Önemli 10 Özellik')
plt.gca().invert_yaxis()

# 3. Tahmin Dağılımı
plt.subplot(2, 3, 3)
pred_counts = pd.Series(y_pred).value_counts()
plt.bar(['Düşük Risk', 'Yüksek Risk'], [pred_counts.get(0, 0), pred_counts.get(1, 0)], color=['green', 'red'])
plt.title('Tahmin Dağılımı')
plt.ylabel('Adet')

# 4. Gerçek Değer Dağılımı
plt.subplot(2, 3, 4)
actual_counts = y_test.value_counts()
plt.bar(['Düşük Risk', 'Yüksek Risk'], [actual_counts.get(0, 0), actual_counts.get(1, 0)], color=['lightgreen', 'lightcoral'])
plt.title('Gerçek Değer Dağılımı')
plt.ylabel('Adet')

# 5. Precision, Recall, F1-Score Karşılaştırması
plt.subplot(2, 3, 5)
from sklearn.metrics import precision_recall_fscore_support
precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
x = ['Precision', 'Recall', 'F1-Score']
width = 0.35
x_pos = range(len(x))
plt.bar([p - width/2 for p in x_pos], [precision[0], recall[0], f1[0]], width, label='Düşük Risk', color='green')
plt.bar([p + width/2 for p in x_pos], [precision[1], recall[1], f1[1]], width, label='Yüksek Risk', color='red')
plt.xlabel('Metrik')
plt.ylabel('Değer')
plt.title('Model Metrikleri')
plt.xticks(x_pos, x)
plt.legend()
plt.ylim([0, 1])

# 6. ROC Curve
plt.subplot(2, 3, 6)
from sklearn.metrics import roc_curve, auc
y_pred_proba = model.predict_proba(X_test)[:, 1]
fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
roc_auc = auc(fpr, tpr)
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.legend(loc="lower right")

plt.tight_layout()
plt.show()








