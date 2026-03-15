#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ML Model GÃ¶rselleÅŸtirme - Korelasyon Matrisi, Confusion Matrix, BaÅŸarÄ± Metrikleri
"""

import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, classification_report
)
import warnings
warnings.filterwarnings('ignore')

# TÃ¼rkÃ§e gÃ¶rselleÅŸtirme desteÄŸi
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# Parametreler
DATA_PATH = "credit_risk_dataset.csv"
MODEL_PATH = "production_model.joblib"
RANDOM_STATE = 42

print("="*60)
print("ML Model GÃ¶rselleÅŸtirme BaÅŸlÄ±yor...")
print("="*60)

try:
    # 1. Veri yÃ¼kle
    print("\n1. Veri yÃ¼kleniyor...")
    df = pd.read_csv(DATA_PATH)
    print(f"   âœ“ {len(df)} satÄ±r, {len(df.columns)} sÃ¼tun yÃ¼klendi")
    
    # 2. Veri Ã¶n iÅŸleme (Model eÄŸitirken yapÄ±ldÄ±ÄŸÄ± gibi)
    print("\n2. Veri Ã¶n iÅŸleme yapÄ±lÄ±yor...")
    
    # Eksik deÄŸerler
    df.fillna(df.median(numeric_only=True), inplace=True)
    
    # One-Hot Encoding (Kategorik sÃ¼tunlar)
    df_processed = pd.get_dummies(
        df, 
        columns=['person_home_ownership', 'loan_intent', 'loan_grade', 'cb_person_default_on_file'],
        drop_first=True
    )
    
    # 3. Model ve veri hazÄ±rla
    print("\n3. Model ve veri hazÄ±rlanÄ±yor...")
    X = df_processed.drop('loan_status', axis=1)
    y = df_processed['loan_status']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    
    # 4. Model yÃ¼kle
    print("\n4. Model yÃ¼kleniyor...")
    model = joblib.load(MODEL_PATH)
    print(f"   âœ“ Model yÃ¼klendi: {type(model).__name__}")
    
    # 5. Tahminler yap
    print("\n5. Tahminler yapÄ±lÄ±yor...")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    print(f"   âœ“ {len(y_pred)} tahmin yapÄ±ldÄ±")
    
    # ============================================
    # VÄ°ZUEL 1: KORELASYON MATRÄ°SÄ° (HEATMAP)
    # ============================================
    print("\n6. Korelasyon Matrisi oluÅŸturuluyor...")
    
    # Ä°lk 15 sayÄ±sal sÃ¼tunu seÃ§ (matrix Ã§ok bÃ¼yÃ¼k olmasÄ±n diye)
    numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()[:15]
    correlation_data = X_train[numeric_cols].copy()
    correlation_matrix = correlation_data.corr()
    
    plt.figure(figsize=(14, 10))
    sns.heatmap(
        correlation_matrix,
        annot=True,  # DeÄŸerleri gÃ¶ster
        fmt='.2f',   # 2 ondalak basamak
        cmap='coolwarm',  # Renk paleti
        center=0,
        cbar_kws={'label': 'Korelasyon'},
        square=True,
        linewidths=0.5,
        linecolor='gray'
    )
    plt.title('Korelasyon Matrisi (Heatmap)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Ã–zellikler', fontsize=12)
    plt.ylabel('Ã–zellikler', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig('correlation_matrix.png', dpi=300, bbox_inches='tight')
    print("   âœ“ Korelasyon Matrisi kaydedildi: correlation_matrix.png")
    plt.close()
    
    # ============================================
    # VÄ°ZUEL 2: CONFUSION MATRIX (KARIÅIKLIK MATRÄ°SÄ°)
    # ============================================
    print("\n7. Confusion Matrix oluÅŸturuluyor...")
    
    cm = confusion_matrix(y_test, y_pred)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        cbar_kws={'label': 'SayÄ±'},
        xticklabels=['SaÄŸlÄ±klÄ±', 'Riskli'],
        yticklabels=['SaÄŸlÄ±klÄ±', 'Riskli'],
        annot_kws={'size': 14, 'weight': 'bold'}
    )
    
    # Etiketler
    plt.title('Confusion Matrix (KarÄ±ÅŸÄ±klÄ±k Matrisi)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Tahmin Edilen (Predicted)', fontsize=12, fontweight='bold')
    plt.ylabel('GerÃ§ek (Actual)', fontsize=12, fontweight='bold')
    
    # CM analizi
    tn, fp, fn, tp = cm.ravel()
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # Metin ekleme
    textstr = f'TP={tp}, FN={fn}\nFP={fp}, TN={tn}\nDuyarlÄ±lÄ±k={sensitivity:.3f}, Ã–zgÃ¼llÃ¼k={specificity:.3f}'
    plt.text(1.5, -0.5, textstr, fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight')
    print("   âœ“ Confusion Matrix kaydedildi: confusion_matrix.png")
    plt.close()
    
    # ============================================
    # VÄ°ZUEL 3: BAÅARI METRÄ°KLERÄ° GRAFÄ°ÄÄ°
    # ============================================
    print("\n8. BaÅŸarÄ± Metrikleri GrafiÄŸi oluÅŸturuluyor...")
    
    # Metrikleri hesapla
    metrics_dict = {
        'Accuracy': accuracy_score(y_test, y_pred),
        'Precision': precision_score(y_test, y_pred, zero_division=0),
        'Recall': recall_score(y_test, y_pred, zero_division=0),
        'F1-Score': f1_score(y_test, y_pred, zero_division=0),
        'ROC-AUC': roc_auc_score(y_test, y_pred_proba),
    }
    
    # GrafiÄŸi oluÅŸtur
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Sol taraf: Bar grafik
    metrics_names = list(metrics_dict.keys())
    metrics_values = list(metrics_dict.values())
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6']
    
    bars = ax1.bar(metrics_names, metrics_values, color=colors, alpha=0.8, edgecolor='black', linewidth=2)
    ax1.set_ylim([0, 1.05])
    ax1.set_ylabel('Skor', fontsize=12, fontweight='bold')
    ax1.set_title('BaÅŸarÄ± Metrikleri (Bar Grafik)', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)
    
    # DeÄŸerleri Ã§ubuk Ã¼zerine yaz
    for bar, value in zip(bars, metrics_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{value:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # SaÄŸ taraf: Radar grafik (Accuracy/F1-Score vurgusu)
    key_metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']
    key_values = [metrics_dict[m] for m in key_metrics]
    
    angles = np.linspace(0, 2 * np.pi, len(key_metrics), endpoint=False).tolist()
    key_values += key_values[:1]
    angles += angles[:1]
    
    ax2 = plt.subplot(122, projection='polar')
    ax2.plot(angles, key_values, 'o-', linewidth=2, color='#3498db', label='Model PerformansÄ±')
    ax2.fill(angles, key_values, alpha=0.25, color='#3498db')
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(key_metrics, fontsize=10)
    ax2.set_ylim([0, 1])
    ax2.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax2.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=9)
    ax2.grid(True, linestyle='--')
    ax2.set_title('Radar Grafik - Performans Ã–zeti', fontsize=14, fontweight='bold', pad=20)
    ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.tight_layout()
    plt.savefig('success_metrics.png', dpi=300, bbox_inches='tight')
    print("   âœ“ BaÅŸarÄ± Metrikleri GrafiÄŸi kaydedildi: success_metrics.png")
    plt.close()
    
    # ============================================
    # DETAYLI RAPOR
    # ============================================
    print("\n" + "="*60)
    print("DETAYLI BAÅARI RAPORU")
    print("="*60)
    
    print("\nğŸ“Š ANALÄ°Z Ã–ZETÄ°:")
    print(f"  â€¢ Test Veri Seti Boyutu: {len(y_test)} Ã¶rnek")
    print(f"  â€¢ Pozitif SÄ±nÄ±f (Riskli): {sum(y_test)} Ã¶rnek ({sum(y_test)/len(y_test)*100:.1f}%)")
    print(f"  â€¢ Negatif SÄ±nÄ±f (SaÄŸlÄ±klÄ±): {len(y_test)-sum(y_test)} Ã¶rnek ({(1-sum(y_test)/len(y_test))*100:.1f}%)")
    
    print("\nğŸ“ˆ BAÅARI METRÄ°KLERÄ°:")
    for metric_name, metric_value in metrics_dict.items():
        bar_length = int(metric_value * 30)
        bar = "â–ˆ" * bar_length + "â–‘" * (30 - bar_length)
        print(f"  â€¢ {metric_name:15s}: {bar} {metric_value:.4f}")
    
    print("\nğŸ¯ CONFUSION MATRIX ANALÄ°ZÄ°:")
    print(f"  â€¢ True Positives (TP):   {tp:5d} - DoÄŸru tahmin edilen riskli")
    print(f"  â€¢ True Negatives (TN):   {tn:5d} - DoÄŸru tahmin edilen saÄŸlÄ±klÄ±")
    print(f"  â€¢ False Positives (FP):  {fp:5d} - YanlÄ±ÅŸ tahmin edilen riskli")
    print(f"  â€¢ False Negatives (FN):  {fn:5d} - YanlÄ±ÅŸ tahmin edilen saÄŸlÄ±klÄ±")
    print(f"  â€¢ DuyarlÄ±lÄ±k (Sensitivity): {sensitivity:.4f}")
    print(f"  â€¢ Ã–zgÃ¼llÃ¼k (Specificity):   {specificity:.4f}")
    
    print("\nğŸ“‹ SINIF RAPORU:")
    print(classification_report(y_test, y_pred, target_names=['SaÄŸlÄ±klÄ±', 'Riskli']))
    
    print("\nâœ… TÃœMDÃœM GRAFIKLER BAÅARIYLA OLUÅTURULDU:")
    print("  1. âœ“ correlation_matrix.png - Korelasyon Matrisi (Heatmap)")
    print("  2. âœ“ confusion_matrix.png - Confusion Matrix (KarÄ±ÅŸÄ±klÄ±k Matrisi)")
    print("  3. âœ“ success_metrics.png - BaÅŸarÄ± Metrikleri GrafiÄŸi")
    print("\n" + "="*60)
    
except FileNotFoundError as e:
    print(f"\nâŒ Hata: Dosya bulunamadÄ± - {e}")
    print("   LÃ¼tfen aÅŸaÄŸÄ±daki dosyalarÄ±n mevcut olduÄŸunu kontrol edin:")
    print(f"   â€¢ {DATA_PATH}")
    print(f"   â€¢ {MODEL_PATH}")
    
except Exception as e:
    print(f"\nâŒ Bir hata oluÅŸtu: {e}")
    import traceback
    traceback.print_exc()

print("\nâœ¨ Script tamamlandÄ±!\n")

