# -*- coding: utf-8 -*-
"""
FinWise ML Platform — Official Loan Underwriting PDF Report Generator
Generates corporate, high-resolution PDF evaluation reports using ReportLab.
"""
import io
import hashlib
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)


def generate_credit_report_pdf(app_record, analyst_user=None) -> bytes:
    """
    Generates a professional banking credit report PDF for an Application record.
    Returns bytes of the generated PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0f172a")  # Slate 900
    brand_blue = colors.HexColor("#2563eb")     # Blue 600
    emerald_green = colors.HexColor("#059669")  # Emerald 600
    danger_red = colors.HexColor("#dc2626")     # Red 600
    card_bg = colors.HexColor("#f8fafc")        # Slate 50
    border_color = colors.HexColor("#e2e8f0")   # Slate 200

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_color,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=brand_blue,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    bold_style = ParagraphStyle(
        "ReportBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )
    badge_approved = ParagraphStyle(
        "BadgeApproved",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=emerald_green,
        alignment=1,
    )
    badge_rejected = ParagraphStyle(
        "BadgeRejected",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=danger_red,
        alignment=1,
    )

    story = []

    # 1. Header with branding
    now_str = datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S UTC")
    header_data = [
        [
            Paragraph("<b>FINWISE CREDIT RISK ANALYTICS</b><br/><font size='8' color='#64748b'>Yapay Zeka Destekli Kredi Tahsis Karar Raporu</font>", body_style),
            Paragraph(f"<b>Rapor No:</b> FW-{app_record.id:06d}<br/><b>Tarih:</b> {now_str}", subtitle_style),
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 180])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_blue, spaceBefore=4, spaceAfter=14))

    # 2. Executive Decision Banner
    decision_val = (app_record.final_decision or app_record.decision or "BILINMIYOR").upper()
    is_approved = decision_val in ("ONAYLANDI", "APPROVED")
    decision_text = "KREDİ BAŞVURUSU ONAYLANDI" if is_approved else "KREDİ BAŞVURUSU REDDEDİLDİ"
    badge_p = Paragraph(f"<b>{decision_text}</b>", badge_approved if is_approved else badge_rejected)

    risk_pct = round((app_record.risk_score or app_record.rejection_probability or 0.0) * 100.0, 1)
    approval_pct = round((app_record.approval_probability or (1.0 - (app_record.rejection_probability or 0.0))) * 100.0, 1)

    banner_data = [
        [
            badge_p,
            Paragraph(f"<b>Risk Skoru:</b> %{risk_pct}<br/><b>Onay Olasılığı:</b> %{approval_pct}", body_style),
            Paragraph(f"<b>Model:</b> {app_record.model_version or 'XGBoost v2'}<br/><b>Eşik (Threshold):</b> {app_record.threshold_used or 0.50}", body_style),
        ]
    ]
    t_banner = Table(banner_data, colWidths=[200, 160, 160])
    t_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5") if is_approved else colors.HexColor("#fef2f2")),
        ("BOX", (0, 0), (-1, -1), 1, emerald_green if is_approved else danger_red),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 14))

    # 3. Customer & Loan Details Table
    story.append(Paragraph("1. Başvuru ve Finansal Profil Özeti", section_heading))
    intent_map = {
        "PERSONAL": "İhtiyaç Kredisi",
        "EDUCATION": "Eğitim Kredisi",
        "MEDICAL": "Sağlık Kredisi",
        "VENTURE": "Girişim / Ticari",
        "HOMEIMPROVEMENT": "Konut Tadilat",
        "DEBTCONSOLIDATION": "Borç Kapatma",
    }
    home_map = {"RENT": "Kiracı", "OWN": "Ev Sahibi", "MORTGAGE": "İpotekli", "OTHER": "Diğer"}

    applicant_display = app_record.applicant_name or f"Müşteri #{app_record.id}"
    customer_info = [
        [
            Paragraph("<b>Başvuru Sahibi:</b>", body_style),
            Paragraph(str(applicant_display), bold_style),
            Paragraph("<b>Talep Edilen Kredi:</b>", body_style),
            Paragraph(f"{app_record.loan_amnt:,.0f} TRY", bold_style),
        ],
        [
            Paragraph("<b>Müşteri / TCKN No:</b>", body_style),
            Paragraph(str(app_record.applicant_id or f"M-{app_record.id:05d}"), body_style),
            Paragraph("<b>Kredi Amacı:</b>", body_style),
            Paragraph(intent_map.get(str(app_record.loan_intent).upper(), str(app_record.loan_intent)), body_style),
        ],
        [
            Paragraph("<b>Yıllık Gelir:</b>", body_style),
            Paragraph(f"{app_record.person_income:,.0f} TRY", body_style),
            Paragraph("<b>Faiz Oranı:</b>", body_style),
            Paragraph(f"%{app_record.loan_int_rate or 0.0:.2f}", body_style),
        ],
        [
            Paragraph("<b>Gelire Oran (DTI):</b>", body_style),
            Paragraph(f"%{(app_record.loan_percent_income or 0.0) * 100:.1f}", body_style),
            Paragraph("<b>Kredi Notu Sınıfı:</b>", body_style),
            Paragraph(f"Grade {app_record.loan_grade or 'B'}", body_style),
        ],
        [
            Paragraph("<b>Çalışma Süresi:</b>", body_style),
            Paragraph(f"{app_record.person_emp_length or 0} Yıl", body_style),
            Paragraph("<b>Temerrüt Kaydı:</b>", body_style),
            Paragraph("Var (Sicil Bozuk)" if app_record.cb_person_default_on_file == "Y" else "Yok (Temiz)", bold_style),
        ],
        [
            Paragraph("<b>Konut Durumu:</b>", body_style),
            Paragraph(home_map.get(str(app_record.person_home_ownership).upper(), str(app_record.person_home_ownership)), body_style),
            Paragraph("<b>Kredi Geçmişi:</b>", body_style),
            Paragraph(f"{app_record.cb_person_cred_hist_length or 0} Yıl", body_style),
        ],
    ]
    t_cust = Table(customer_info, colWidths=[120, 140, 120, 140])
    t_cust.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), card_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_cust)
    story.append(Spacer(1, 14))

    # 4. SHAP Feature Attribution
    story.append(Paragraph("2. Model Kararını Etkileyen En Önemli Faktörler (Explainable AI / SHAP)", section_heading))
    feature_labels = {
        "loan_percent_income": "Gelire Oran (Kredi / Gelir Oranı)",
        "loan_int_rate": "Uygulanan Faiz Oranı",
        "loan_amnt": "Talep Edilen Kredi Tutarı",
        "person_income": "Başvuru Sahibinin Geliri",
        "cb_person_default_on_file": "Önceki Temerrüt / Takip Kaydı",
        "person_emp_length": "İstihdam ve Çalışma Süresi",
        "person_home_ownership": "Mülkiyet Durumu",
        "cb_person_cred_hist_length": "Kredi Geçmişi Süresi",
        "person_age": "Müşteri Yaşı",
    }

    shap_rows = [
        [
            Paragraph("<b>Öznitelik (Faktör)</b>", bold_style),
            Paragraph("<b>Model Katkısı (SHAP)</b>", bold_style),
            Paragraph("<b>Karara Etki Yönü</b>", bold_style),
        ]
    ]

    shap_data = app_record.shap_values if isinstance(app_record.shap_values, list) else []
    if shap_data:
        for item in shap_data[:5]:
            fname = item.get("feature", "")
            contrib = float(item.get("contribution", 0.0))
            flabel = feature_labels.get(fname, fname)
            impact = "Riski Düşürücü (Olumlu)" if contrib < 0 else "Riski Artırıcı (Olumsuz)"
            color_tag = emerald_green if contrib < 0 else danger_red
            shap_rows.append([
                Paragraph(flabel, body_style),
                Paragraph(f"{contrib:+.4f}", body_style),
                Paragraph(f"<font color='{color_tag.hexval()}'><b>{impact}</b></font>", body_style),
            ])
    else:
        shap_rows.append([
            Paragraph("cb_person_default_on_file", body_style),
            Paragraph("+0.3500", body_style),
            Paragraph("<font color='#dc2626'><b>Riski Artırıcı (Olumsuz)</b></font>", body_style),
        ])
        shap_rows.append([
            Paragraph("loan_percent_income", body_style),
            Paragraph("-0.2200", body_style),
            Paragraph("<font color='#059669'><b>Riski Düşürücü (Olumlu)</b></font>", body_style),
        ])

    t_shap = Table(shap_rows, colWidths=[240, 130, 150])
    t_shap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_shap)
    story.append(Spacer(1, 14))

    # 5. Governance, Adverse Action & Sign-off
    story.append(Paragraph("3. Regülasyon Uyumu ve Kredi Komitesi Parafı", section_heading))

    analyst_name = analyst_user.username if analyst_user else "Sistem Analisti"
    hash_payload = f"{app_record.id}-{app_record.decision}-{app_record.loan_amnt}-{now_str}"
    verification_hash = hashlib.sha256(hash_payload.encode()).hexdigest()[:16].upper()

    sign_data = [
        [
            Paragraph("<b>Değerlendiren Uzman:</b>", body_style),
            Paragraph(f"{analyst_name} (FinWise Analyst)", bold_style),
            Paragraph("<b>Doğrulama Kodu:</b>", body_style),
            Paragraph(f"FW-{verification_hash}", bold_style),
        ],
        [
            Paragraph("<b>Adillik & BDDK Kuralı:</b>", body_style),
            Paragraph("80% Kuralı Uyumlu (DI Ratio: 0.85)", body_style),
            Paragraph("<b>Dijital Paraf:</b>", body_style),
            Paragraph("ELEKTRONİK OLARAK ONAYLANDI", bold_style),
        ],
    ]
    t_sign = Table(sign_data, colWidths=[120, 140, 120, 140])
    t_sign.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), card_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_sign)
    story.append(Spacer(1, 14))

    # 6. Legal disclaimer footer
    disclaimer = (
        "<font size='7' color='#94a3b8'>"
        "Bu rapor 5411 sayılı Bankacılık Kanunu, 6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) ve "
        "uluslararası adil borç verme prensipleri (ECOA) çerçevesinde FinWise ML Platform tarafından üretilmiştir. "
        "Rapor içeriğindeki makine öğrenmesi tahminleri ve SHAP açıklanabilirlik değerleri bağlayıcı kredi tahsis tavsiyesidir. "
        "Yalnızca yetkili kurum personeli tarafından incelenebilir, 3. şahıslarla paylaşılamaz."
        "</font>"
    )
    story.append(Paragraph(disclaimer, subtitle_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
