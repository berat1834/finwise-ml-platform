import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.models.models import get_db_session, NLPTrainingData

def get_default_data():
    return [
        # Neden / Sebepler (reasons)
        ("Neden reddedildim?", "reasons"),
        ("Bu kararin nedeni nedir?", "reasons"),
        ("Hangi faktorler etkili oldu?", "reasons"),
        ("Red sebebi ne?", "reasons"),
        ("Kararin arkasindaki 3 sebep nedir?", "reasons"),
        ("Bu kararin en onemli 3 nedeni nedir?", "reasons"),
        ("Sebep ne?", "reasons"),
        ("Neden onaylanmadi?", "reasons"),
        
        # Limit (limit)
        ("Ne kadar kredi alabilirim?", "limit"),
        ("Kredi limitim nedir?", "limit"),
        ("Bana ne kadar kredi cikar?", "limit"),
        ("Alabilecegim maksimum tutar ne kadar?", "limit"),
        ("Limitim ne?", "limit"),
        ("Kredi tutari ne olmali?", "limit"),
        
        # Iyilesme (improvement)
        ("Onay olasiligini artirmak icin ne yapmaliyim?", "improvement"),
        ("Nasil onay alirim?", "improvement"),
        ("Kredi notumu nasil yukseltirim?", "improvement"),
        ("Onay ihtimalini artirmak icin tavsiye", "improvement"),
        ("Ne yaparsam onaylanir?", "improvement"),
        ("Tavsiyeleriniz nelerdir?", "improvement"),
        
        # Risk (risk_level)
        ("Risk seviyesi nedir?", "risk_level"),
        ("Bu musteri icin risk seviyesi nedir?", "risk_level"),
        ("Risk durumu nedir?", "risk_level"),
        ("Musterinin riski yuksek mi?", "risk_level"),
        ("Risk yuzdesi kac?", "risk_level"),
        ("Guvenilir mi?", "risk_level"),

        # Faiz (interest_rate)
        ("Faiz orani nedir?", "interest_rate"),
        ("Kredi faiziniz ne kadar?", "interest_rate"),
        ("Yuzde kac faiz biniyor?", "interest_rate"),
        ("Aylik faiz ne kadar?", "interest_rate"),
        ("Faiz orani yuzde kactir?", "interest_rate"),
        
        # Belgeler (documents)
        ("Hangi belgeler gerekli?", "documents"),
        ("Kefil istiyor musunuz?", "documents"),
        ("Istenen evraklar nelerdir?", "documents"),
        ("Basvuru icin ne lazim?", "documents"),
        ("Gelir belgesi sart mi?", "documents"),

        # Iletisim (contact)
        ("Musteri hizmetleri numarasi ne?", "contact"),
        ("Size nasil ulasirim?", "contact"),
        ("Sube nerede?", "contact"),
        ("Telefon numaraniz nedir?", "contact"),
        ("Destek hatti var mi?", "contact")
    ]

def train_and_save():
    print("Yerel NLP Modeli (Niyet Siniflandirma) Egitiliyor...")
    
    session = get_db_session()
    
    try:
        # Check if we have data in DB
        db_records = session.query(NLPTrainingData).filter(NLPTrainingData.intent != 'unknown').all()
        
        if not db_records:
            print("Veritabaninda egitim verisi bulunamadi, varsayilan veriler yukleniyor...")
            default_data = get_default_data()
            for q, i in default_data:
                record = NLPTrainingData(question=q, intent=i, confidence=1.0, source='human')
                session.add(record)
            session.commit()
            db_records = session.query(NLPTrainingData).filter(NLPTrainingData.intent != 'unknown').all()
            print(f"{len(default_data)} adet varsayilan veri DB'ye eklendi.")
        else:
            print(f"Veritabanindan {len(db_records)} adet egitim verisi cekildi.")
            
        X = [item.question for item in db_records]
        y = [item.intent for item in db_records]
        
    except Exception as e:
        print(f"Veritabani hatasi: {e}. Varsayilan veri setine geciliyor...")
        default_data = get_default_data()
        X = [item[0] for item in default_data]
        y = [item[1] for item in default_data]

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), analyzer='word')),
        ('clf', LogisticRegression(random_state=42, class_weight='balanced', max_iter=200))
    ])

    pipeline.fit(X, y)

    joblib.dump(pipeline, 'local_nlp_intent.joblib')
    print("Model basariyla 'local_nlp_intent.joblib' olarak kaydedildi!")

if __name__ == "__main__":
    train_and_save()
