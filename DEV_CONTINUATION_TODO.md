# FinWise Dev Continuation TODO

Bu dosya, VS Code yeniden acildiginda kaldigimiz yerden devam etmek icin hazirlandi.

## Son Durum (Tamamlandi)
- [x] AI Risk Chat paneli sonuc ekranina eklendi
- [x] Fairness context otomatik baglandi
- [x] Sohbet gecmisi tur bazli gosterim eklendi
- [x] Kaynak badge gorunurlugu guclendirildi (ready, deterministic, llm, unknown)
- [x] Yanit turu ve guven etiketleri Turkcelestirildi
- [x] Sohbet gecmisi basvuru bazli localStorage kaliciligi eklendi
- [x] Sohbet turu zaman damgasi eklendi
- [x] Regresyon testi calisti: test_api_v2.py (PASS)
- [x] API smoke run kaydi olusturuldu: SMOKE_TEST_RUN_2026-03-13.md (4/4 PASS)
- [x] UI smoke sonuclari raporlandi: 2 PASS / 2 FAIL / 1 SKIP
- [x] Model class-order kaynakli karar/olasilik tersligi icin backend mapping duzeltildi
- [x] UI senaryo yeniden dogrulamasi tamamlandi: 3/3 PASS (esik kurali aciklandi)
- [x] Modern UI tasarımı (Tailwind CSS + Alpine.js) uygulandı
- [x] Entegre Login ve AI Asistan paneli arayüze eklendi

## Acik Isler (Siradaki)
- [ ] Gecmisi temizle akisini tekrar manuel dogrula (dusuk oncelik)
- [ ] Basvuru gecis baglami etiketini tekrar manuel dogrula (dusuk oncelik)

## Yeni Backlog (Kaydedildi - 2026-03-13)

### P0 - Bu Oturumda Baslananlar (2026-03-13)
- [x] Offers funnel dashboard endpointi eklendi (trend + banka/dil kirilimi)
- [x] Offers event endpointi icin rate limiting eklendi
- [x] Startup diagnostics endpointi eklendi (/health/startup)
- [x] Partner banka adaptor katmani iskeleti eklendi (timeout/retry + fallback mock)
- [x] Teklif endpointi adaptor katmanina baglandi ve lead fallback cevabi eklendi
- [x] Lead fallback endpointi eklendi (/api/v2/offers/lead)
- [x] Frontend lead fallback modal/submit akisi eklendi
- [x] Dashboard cevabina adaptor telemetri metrikleri eklendi

### P0 - Sonuc Sonrasi Teklif ve Yonlendirme (En Yuksek Etki)
- [ ] Onayli basvuru sonucu icin "Teklifleri Gor" adimi ekle
- [ ] Coklu banka teklif karti UI (3-5 teklif) tasarla
- [ ] Kart alanlari: faiz araligi, vade, aylik odeme, toplam geri odeme, ek masraf
- [ ] CTA butonlari: "Bankaya Git" ve "Basvuruyu Paylas"
- [ ] Teklif tiklama takip olayi (impression, click, start)

### P0 - Uyum ve Guvenlik
- [ ] Acik riza modalini ekle (hangi veri hangi bankayla paylasilacak)
- [ ] Siralama seffafligi metni ekle (neden bu teklif ustte)
- [ ] Sponsorlu teklif etiketlemesi ekle
- [ ] Veri paylasim audit log kaydi (kim, ne zaman, hangi veri)

### P1 - Entegrasyon ve Fallback
- [ ] Partner banka adaptor katmani olustur (mock ile basla)
- [ ] Banka API timeout/retry stratejisi ekle
- [ ] API yoksa fallback: lead form + callback akisi
- [ ] Teklif bulunamazsa "manuele aktarim" UX fallback'i ekle

### P1 - Donusum ve Analitik
- [ ] Funnel olcumleri: decision -> offers_view -> offer_click -> apply_start -> apply_complete
- [ ] Teklif performans paneli (CTR, basvuru baslatma orani)
- [ ] A/B test: teklif siralama ve CTA metin varyantlari

### P1 - Uretim Hazirlik Ozellikleri (Yeni)
- [x] Gercek banka adaptor katmani (provider bazli, timeout/retry/fallback) - DONE
- [x] Teklif kalite skoru ve guven puani (confidence_score + data_freshness_sec) - DONE
- [x] A/B test altyapisi (ab-variant endpoint + offers/mock ab_variant sorting) - DONE
- [x] /api/v2/offers/adapter-health endpoint (ping + overall status) - DONE
- [x] Prometheus adapter telemetry gauges (attempts/success/fail/fallback per bank) - DONE
- [x] .env.example guncellendi (BANK_API_*_URL, BANK_API_TIMEOUT_SEC, OFFERS_AB_SPLIT_PERCENT) - DONE
   - [x] Anti-fraud/suistimal korumasi (IP burst + lead burst + session dedup) - DONE
   - [x] Operasyonel gozlemlenebilirlik (DB ping + model MD5 in /health/startup) - DONE
   - [x] /api/v2/offers/fraud-stats admin endpoint - DONE
   - [x] /api/v2/simulate/approval re-degerlendirme simulatoru (no DB write) - DONE

### P2 - Karar Sonrasi Deger Katacak Ozellikler
- [x] "Onayi artirma onerileri" paneli (heuristic scenario suggestions + delta) - DONE
- [x] Yeniden degerlendirme simulasyonu (tutar/vade degisince olasilik degisimi) - DONE
- [ ] Belge checklist + basvuru hazirlik skoru
- [ ] Basit fraud/suistimal sinyalleri (hizli tekrar basvuru, cihaz sinyali)

### P2 - Son I18N Tamamlama/Kalite
- [ ] Tum popup/metinler icin TR/EN son smoke (manual)
- [ ] PDF/CSV indirme metinlerinin EN gorunumu manuel kontrol
- [ ] Dil degisimi sirasinda aktif chat state regresssion kontrolu

## Uygulama Sirası (Onerilen)
1. Teklif karti UI + mock API + event tracking
2. Acik riza ve seffaflik/sponsor etiketleri
3. Banka adaptor/fallback akislari
4. Simulasyon ve onay artirma yardimlari

## Sonraki Oturumda Ilk 30 Dakika Plani
1. "Teklifleri Gor" butonunu sonuc ekranina ekle
2. Mock teklif endpoint'i olustur (sabit 3 banka)
3. Teklif kartlarini bu endpoint'ten doldur
4. Teklif tiklama event'ini local log'a yaz

## VS Code Yeniden Acildiginda
1. Bu dosyayi ac: DEV_CONTINUATION_TODO.md
2. Gerekirse test calistir:
   - .venv\Scripts\python.exe test_api_v2.py
3. Sonraki adim olarak P0 backlog'tan ilerle:
   - Sonuc ekranina "Teklifleri Gor" adimi ekle

## Hemen Sonraki Teknik Adim (Onaydan Sonra)
- Sonuc ekranina "Teklifleri Gor" entry point'i ekle
- Teklif kartlarini gosteren mock paneli ac
- Event takiplerini yazmaya basla ve smoke ile dogrula

## Not
- Bu proje klasorunde git repo algilanmadi, bu nedenle commit akisi su an yok.
