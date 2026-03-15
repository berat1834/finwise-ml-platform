# -*- coding: utf-8 -*-
"""
Kredi Risk Analizi - Müşteri Başvuru Değerlendirme Sistemi
"""
import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

class KrediRiskSistemi:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        
    def model_egit(self, veri_yolu='credit_risk_dataset.csv'):
        """Modeli eğitir ve kaydeder"""
        print("Model eğitiliyor...")
        
        # Veri yükleme
        data = pd.read_csv(veri_yolu)
        
        # Eksik değerleri doldurma
        data.fillna(data.median(numeric_only=True), inplace=True)
        
        # Kategorik verileri dönüştürme (One-Hot Encoding)
        data = pd.get_dummies(data, columns=['person_home_ownership', 'loan_intent', 
                                             'loan_grade', 'cb_person_default_on_file'], 
                              drop_first=True)
        
        # Özellikler (X) ve hedef değişken (y)
        X = data.drop(columns=['loan_status'])
        y = data['loan_status']
        
        # Sütun isimlerini kaydet
        self.feature_columns = X.columns.tolist()
        
        # Eğitim ve test setine bölme
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # Random Forest Modeli
        self.model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
        self.model.fit(X_train, y_train)
        
        # Tahmin yapma
        y_pred = self.model.predict(X_test)
        
        # Model performansı
        print("\n" + "="*50)
        print("MODEL PERFORMANSI")
        print("="*50)
        print(f"Doğruluk Skoru: %{accuracy_score(y_test, y_pred)*100:.2f}")
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Modeli kaydet
        with open("kredi_risk_model.pkl", "wb") as file:
            pickle.dump(self.model, file)
        
        with open("feature_columns.pkl", "wb") as file:
            pickle.dump(self.feature_columns, file)
            
        print("\nModel başarıyla kaydedildi!")
        
        # Grafikleri göster
        self._grafikleri_goster(X, X_test, y_test, y_pred)
        
        return self.model
    
    def model_yukle(self):
        """Kaydedilmiş modeli yükler"""
        try:
            with open("kredi_risk_model.pkl", "rb") as file:
                self.model = pickle.load(file)
            with open("feature_columns.pkl", "rb") as file:
                self.feature_columns = pickle.load(file)
            print("Model başarıyla yüklendi!")
            return True
        except FileNotFoundError:
            print("Model dosyası bulunamadı. Önce modeli eğitmeniz gerekiyor.")
            return False
    
    def kredi_degerlendir(self, musteri_bilgileri):
        """
        Müşteri bilgilerine göre kredi başvurusunu değerlendirir
        
        Parametreler:
        - person_age: Yaş
        - person_income: Yıllık gelir
        - person_emp_length: İş deneyimi (yıl)
        - loan_amnt: Talep edilen kredi miktarı
        - loan_int_rate: Faiz oranı
        - loan_percent_income: Gelirin yüzdesi olarak kredi
        - cb_person_cred_hist_length: Kredi geçmişi uzunluğu
        - person_home_ownership: Ev sahibi mi? (RENT, OWN, MORTGAGE, OTHER)
        - loan_intent: Kredi amacı (PERSONAL, EDUCATION, MEDICAL, VENTURE, HOMEIMPROVEMENT, DEBTCONSOLIDATION)
        - loan_grade: Kredi notu (A, B, C, D, E, F, G)
        - cb_person_default_on_file: Geçmiş ödeme geçmişi (Y, N)
        """
        
        if self.model is None:
            print("Model yüklü değil!")
            return None
        
        # DataFrame oluştur
        df = pd.DataFrame([musteri_bilgileri])
        
        # Kategorik değişkenleri encode et
        df = pd.get_dummies(df, columns=['person_home_ownership', 'loan_intent', 
                                        'loan_grade', 'cb_person_default_on_file'], 
                           drop_first=True)
        
        # Eğitim sırasında kullanılan tüm sütunları ekle (eksik olanlar 0 olacak)
        for col in self.feature_columns:
            if col not in df.columns:
                df[col] = 0
        
        # Sütunları aynı sıraya koy
        df = df[self.feature_columns]
        
        # Tahmin yap
        tahmin = self.model.predict(df)[0]
        olasilik = self.model.predict_proba(df)[0]
        
        # Sonuçları göster
        print("\n" + "="*60)
        print("KREDİ DEĞERLENDİRME SONUCU")
        print("="*60)
        print(f"\nMüşteri Bilgileri:")
        print(f"  • Yaş: {musteri_bilgileri['person_age']}")
        print(f"  • Yıllık Gelir: ${musteri_bilgileri['person_income']:,.2f}")
        print(f"  • İş Deneyimi: {musteri_bilgileri['person_emp_length']} yıl")
        print(f"  • Talep Edilen Kredi: ${musteri_bilgileri['loan_amnt']:,.2f}")
        print(f"  • Faiz Oranı: %{musteri_bilgileri['loan_int_rate']}")
        print(f"  • Ev Durumu: {musteri_bilgileri['person_home_ownership']}")
        print(f"  • Kredi Amacı: {musteri_bilgileri['loan_intent']}")
        print(f"  • Kredi Notu: {musteri_bilgileri['loan_grade']}")
        
        print(f"\nTahmin Olasılıkları:")
        print(f"  • Kredi Onaylama Olasılığı: %{olasilik[0]*100:.2f}")
        print(f"  • Kredi Reddetme Olasılığı: %{olasilik[1]*100:.2f}")
        
        if tahmin == 0:
            print(f"\n✓ SONUÇ: KREDİ ONAYLANDI")
            print(f"   Müşteriye kredi verilebilir.")
        else:
            print(f"\n✗ SONUÇ: KREDİ REDDEDİLDİ")
            print(f"   Müşteri risk profili yüksek.")
        
        print("="*60 + "\n")
        
        return {
            'tahmin': 'ONAYLANDI' if tahmin == 0 else 'REDDEDİLDİ',
            'onay_olasiligi': olasilik[0],
            'red_olasiligi': olasilik[1]
        }
    
    def _grafikleri_goster(self, X, X_test, y_test, y_pred):
        """Model performans grafiklerini gösterir"""
        plt.figure(figsize=(15, 10))
        
        # 1. Confusion Matrix Heatmap
        plt.subplot(2, 3, 1)
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
        plt.title('Confusion Matrix')
        plt.ylabel('Gerçek Değer')
        plt.xlabel('Tahmin')
        
        # 2. Feature Importance
        plt.subplot(2, 3, 2)
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False).head(10)
        plt.barh(feature_importance['feature'], feature_importance['importance'])
        plt.xlabel('Önem Derecesi')
        plt.title('En Önemli 10 Özellik')
        plt.gca().invert_yaxis()
        
        # 3. Tahmin Dağılımı
        plt.subplot(2, 3, 3)
        pred_counts = pd.Series(y_pred).value_counts()
        plt.bar(['Onaylanan', 'Reddedilen'], 
                [pred_counts.get(0, 0), pred_counts.get(1, 0)], 
                color=['green', 'red'])
        plt.title('Tahmin Dağılımı')
        plt.ylabel('Adet')
        
        # 4. Gerçek Değer Dağılımı
        plt.subplot(2, 3, 4)
        actual_counts = y_test.value_counts()
        plt.bar(['Onaylanan', 'Reddedilen'], 
                [actual_counts.get(0, 0), actual_counts.get(1, 0)], 
                color=['lightgreen', 'lightcoral'])
        plt.title('Gerçek Değer Dağılımı')
        plt.ylabel('Adet')
        
        # 5. Precision, Recall, F1-Score
        plt.subplot(2, 3, 5)
        from sklearn.metrics import precision_recall_fscore_support
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
        x = ['Precision', 'Recall', 'F1-Score']
        width = 0.35
        x_pos = range(len(x))
        plt.bar([p - width/2 for p in x_pos], [precision[0], recall[0], f1[0]], 
                width, label='Onaylanan', color='green')
        plt.bar([p + width/2 for p in x_pos], [precision[1], recall[1], f1[1]], 
                width, label='Reddedilen', color='red')
        plt.xlabel('Metrik')
        plt.ylabel('Değer')
        plt.title('Model Metrikleri')
        plt.xticks(x_pos, x)
        plt.legend()
        plt.ylim([0, 1])
        
        # 6. ROC Curve
        plt.subplot(2, 3, 6)
        from sklearn.metrics import roc_curve, auc
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, color='darkorange', lw=2, 
                label=f'ROC curve (AUC = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.legend(loc="lower right")
        
        plt.tight_layout()
        plt.show()


def main():
    sistem = KrediRiskSistemi()
    
    print("="*60)
    print("KREDİ RİSK ANALİZİ SİSTEMİ")
    print("="*60)
    
    # Modeli eğit veya yükle
    print("\n1. Mevcut modeli kullan")
    print("2. Modeli yeniden eğit")
    
    secim = input("\nSeçiminiz (1/2): ").strip()
    
    if secim == "2":
        sistem.model_egit('credit_risk_dataset.csv')
    else:
        if not sistem.model_yukle():
            print("\nModel bulunamadı, yeni model eğitiliyor...")
            sistem.model_egit('credit_risk_dataset.csv')
    
    # Kullanıcı girdisi ile kredi değerlendirme
    while True:
        print("\n" + "="*60)
        print("YENİ KREDİ BAŞVURUSU")
        print("="*60)
        
        try:
            musteri = {
                'person_age': int(input("\nYaş: ")),
                'person_income': float(input("Yıllık Gelir ($): ")),
                'person_emp_length': float(input("İş Deneyimi (yıl): ")),
                'loan_amnt': float(input("Talep Edilen Kredi Miktarı ($): ")),
                'loan_int_rate': float(input("Faiz Oranı (%): ")),
                'loan_percent_income': 0,  # Otomatik hesaplanacak
                'cb_person_cred_hist_length': float(input("Kredi Geçmişi Uzunluğu (yıl): ")),
            }
            
            # Kredi/gelir oranını hesapla
            musteri['loan_percent_income'] = musteri['loan_amnt'] / musteri['person_income']
            
            print("\nEv Durumu:")
            print("1. RENT (Kiracı)")
            print("2. OWN (Ev Sahibi)")
            print("3. MORTGAGE (İpotekli)")
            print("4. OTHER (Diğer)")
            ev_secim = input("Seçim (1-4): ").strip()
            ev_durumu = {'1': 'RENT', '2': 'OWN', '3': 'MORTGAGE', '4': 'OTHER'}
            musteri['person_home_ownership'] = ev_durumu.get(ev_secim, 'RENT')
            
            print("\nKredi Amacı:")
            print("1. PERSONAL (Kişisel)")
            print("2. EDUCATION (Eğitim)")
            print("3. MEDICAL (Sağlık)")
            print("4. VENTURE (İş Kurma)")
            print("5. HOMEIMPROVEMENT (Ev Geliştirme)")
            print("6. DEBTCONSOLIDATION (Borç Birleştirme)")
            amac_secim = input("Seçim (1-6): ").strip()
            amac = {'1': 'PERSONAL', '2': 'EDUCATION', '3': 'MEDICAL', 
                   '4': 'VENTURE', '5': 'HOMEIMPROVEMENT', '6': 'DEBTCONSOLIDATION'}
            musteri['loan_intent'] = amac.get(amac_secim, 'PERSONAL')
            
            print("\nKredi Notu:")
            print("A, B, C, D, E, F, G (A en iyi, G en kötü)")
            musteri['loan_grade'] = input("Kredi Notu: ").strip().upper()
            
            print("\nGeçmişte Ödeme Temerrüdü var mı?")
            print("1. Hayır")
            print("2. Evet")
            temerrut_secim = input("Seçim (1/2): ").strip()
            musteri['cb_person_default_on_file'] = 'N' if temerrut_secim == '1' else 'Y'
            
            # Değerlendirme
            sistem.kredi_degerlendir(musteri)
            
        except ValueError as e:
            print(f"\nHata: Geçersiz değer girdiniz. {e}")
            continue
        except KeyboardInterrupt:
            print("\n\nProgram sonlandırıldı.")
            break
        
        devam = input("\nBaşka bir başvuru değerlendirmek ister misiniz? (E/H): ").strip().upper()
        if devam != 'E':
            break
    
    print("\nSistem kapatılıyor...")


if __name__ == "__main__":
    main()
