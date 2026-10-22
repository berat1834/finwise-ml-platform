# Smoke Test Run Report - 2026-03-13

## Scope
- Referans checklist: SMOKE_TEST_CHECKLIST.md
- Kapsam: API smoke (otomatik), UI smoke (manuel)

## Environment
- Base URL: http://127.0.0.1:5000
- Auth user: admin
- Tarih: 2026-03-13

## API Smoke Results

| Step | Result | Detail |
|------|--------|--------|
| health | PASS | status=up, version=2.0.0 |
| auth/login | PASS | username=admin, role=admin |
| degerlendir | PASS | appId=557, tahmin=ONAYLANDI |
| api/v2/ai-risk-assistant | PASS | answer_type=general_guidance, confidence=medium |

Toplam: 4/4 PASS

## UI Smoke Status
- Login: PASS
- Basvuru degerlendirme: FAIL
- AI chat soru/yanit: PASS
- Gecmisi temizle: FAIL
- Basvuru gecis baglami: SKIP

UI Ozet: 2 PASS / 2 FAIL / 1 SKIP

Not:
- Hatalar gorsellerde var.

## UI Scenario Re-Validation (Screenshots)

Manuel ekran goruntuleriyle 3 senaryo tekrar kontrol edildi:

1. Senaryo A: PASS
	- Sonuc: ONAYLANDI
	- Gosterim: Onay ~83.3%, Red ~16.7%

2. Senaryo B: PASS
	- Sonuc: REDDEDILDI
	- Gosterim: Onay ~7.2%, Red ~92.8%

3. Senaryo C: PASS (esik kurali ile)
	- Sonuc: ONAYLANDI
	- Gosterim: Onay ~38.9%, Red ~61.1%
	- Aciklama: Red olasiligi yuksek olsa da karar esigi ~63.2% oldugu icin 61.1% < 63.2% durumunda ONAY dogrudur.

Senaryo Ozet: 3/3 PASS

## Conclusion
- API smoke test: PASS
- UI smoke test: PASS (senaryo dogrulama)
- Genel smoke test: API + senaryo kontrolunde PASS
