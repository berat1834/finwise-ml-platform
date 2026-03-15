import re
import argparse
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Font Registration ---
# UTF-8 uyumlu bir font kaydedin. DejaVuSans yaygındır. Bulunamazsa Arial'a geri dönün.
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    FONT_NAME = 'DejaVuSans'
except Exception:
    try:
        # Windows sistemlerinde Arial genellikle C:\Windows\Fonts altında bulunur
        arial_path = Path(r"C:\Windows\Fonts\arial.ttf")
        arial_bold_path = Path(r"C:\Windows\Fonts\arialbd.ttf")
        if arial_path.exists():
            pdfmetrics.registerFont(TTFont('Arial', str(arial_path)))
            if arial_bold_path.exists():
                pdfmetrics.registerFont(TTFont('Arial-Bold', str(arial_bold_path)))
            FONT_NAME = 'Arial'
        else:
            pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
            FONT_NAME = 'Arial'
    except Exception:
        # Varsayılana geri dön
        FONT_NAME = 'Helvetica'

print(f"Kullanılan yazı tipi: {FONT_NAME}")

# --- Argümanları Ayrıştırma ---
parser = argparse.ArgumentParser(description="Markdown dosyasını gelişmiş stillerle PDF'e dönüştürür.")
parser.add_argument(
    "markdown_file", 
    nargs='?', 
    default="ACADEMIC_PAPER_TR.md",
    help="Dönüştürülecek Markdown dosyasının adı. (Varsayılan: ACADEMIC_PAPER_TR.md)"
)
parser.add_argument(
    "-o", "--output", 
    help="Oluşturulacak PDF dosyasının adı. Belirtilmezse, girdi adından türetilir."
)
parser.add_argument(
    "-t", "--theme",
    choices=["screen", "print"],
    default="screen",
    help="PDF teması: 'screen' (koyu tema, ekran için) veya 'print' (açık tema, yazıcı dostu). Varsayılan: screen"
)
args = parser.parse_args()

# Dosya adlarını belirle
md_filename = args.markdown_file
pdf_filename = args.output if args.output else md_filename.replace('.md', '_screen.pdf' if args.theme == 'screen' else '_print.pdf')

# Markdown dosyasını oku
md_path = Path(md_filename)
with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

# PDF dosyasını oluştur
pdf_path = Path(pdf_filename)
doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch, leftMargin=0.75*inch, rightMargin=0.75*inch)

# --- Stiller ---
styles = getSampleStyleSheet()
story = []

# Tema seçimi (Screen vs Print)
THEME = args.theme
if THEME == "print":
    # Yazıcı dostu tema: Açık arka plan, koyu metin
    CODE_BG = colors.HexColor('#f5f5f5')  # Açık gri
    CODE_TEXT = colors.HexColor('#1f2937')  # Koyu gri
    print("🖨️ Yazıcı dostu tema kullanılıyor")
else:
    # Ekran teması: Koyu arka plan, açık metin
    CODE_BG = colors.HexColor('#1f2937')  # Koyu gri (mevcut)
    CODE_TEXT = colors.HexColor('#e5e7eb')  # Açık gri (mevcut)
    print("💻 Ekran teması kullanılıyor")

# Özel stiller
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontName=FONT_NAME,
    fontSize=22,
    textColor=colors.HexColor('#1e3a8a'),
    spaceAfter=14,
    leading=28
)

heading2_style = ParagraphStyle(
    'CustomHeading2',
    parent=styles['Heading2'],
    fontName=FONT_NAME,
    fontSize=16,
    textColor=colors.HexColor('#1e40af'),
    spaceAfter=12,
    spaceBefore=12,
    leading=20
)

heading3_style = ParagraphStyle(
    'CustomHeading3',
    parent=styles['Heading3'],
    fontName=FONT_NAME,
    fontSize=12,
    textColor=colors.HexColor('#2563eb'),
    spaceAfter=8,
    spaceBefore=10,
    leading=16
)

normal_style = ParagraphStyle(
    'CustomNormal',
    parent=styles['Normal'],
    fontName=FONT_NAME,
    fontSize=10.5,
    alignment=4,  # Justify
    spaceAfter=12,
    leading=15 # Line spacing
)

code_style = ParagraphStyle(
    'Code',
    parent=styles['Normal'],
    fontName='Courier',
    fontSize=9,
    textColor=CODE_TEXT,
    backColor=CODE_BG,
    borderPadding=8,
    spaceAfter=12,
    leading=12
)

# --- Ayrıştırma Mantığı ---
lines = md_content.split('\n')
i = 0
while i < len(lines):
    line = lines[i]

    if line.startswith('# '):
        title = line.replace('# ', '').strip()
        story.append(Paragraph(title, title_style))
        i += 1
    elif line.startswith('## '):
        heading = line.replace('## ', '').strip()
        story.append(Paragraph(heading, heading2_style))
        i += 1
    elif line.startswith('### '):
        subheading = line.replace('### ', '').strip()
        story.append(Paragraph(subheading, heading3_style))
        i += 1
    elif line.strip() == '---': # Sayfa sonu veya ayırıcı
        story.append(Spacer(1, 0.2*inch))
        i += 1
    elif line.strip() == '':
        story.append(Spacer(1, 0.1*inch))
        i += 1
    elif line.strip().startswith('|'):
        table_data = []
        header_line = line.split('|')[1:-1]
        i += 1
        # Ayırıcı satırı atla (örn: |---|---|)
        if i < len(lines) and '---' in lines[i]:
            i += 1
        
        while i < len(lines) and lines[i].strip().startswith('|'):
            cells = [cell.strip() for cell in lines[i].split('|')[1:-1]]
            table_data.append(cells)
            i += 1

        if table_data:
            # Başlığı ve veri satırlarını birleştir
            full_table_data = [[h.strip() for h in header_line]] + table_data
            
            table = Table(full_table_data, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), f"{FONT_NAME}-Bold" if FONT_NAME != 'Helvetica' else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f3f4f6')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.15*inch))
        else:
             i +=1 # Başlık var ama veri yoksa ilerle
    elif line.strip().startswith('```'):
        code_lines = []
        i += 1  # ` başlangıcını atla
        while i < len(lines) and not lines[i].strip().startswith('```'):
            code_lines.append(lines[i].replace('\t', '    ')) # Tab'ları boşlukla değiştir
            i += 1
        i += 1  # ` bitişini atla
        
        # ReportLab'in <pre> etiketini kullanarak boşlukları koru
        code_text = "<br/>".join(code_lines)
        story.append(Paragraph(f"<pre>{code_text}</pre>", code_style))

    elif line.strip().startswith(('* ', '- ')):
        text = re.sub(r'^[\*\-]\s+', '• ', line).strip()
        story.append(Paragraph(text, normal_style))
        i += 1
    elif re.match(r'^\d+\.\s+', line.strip()):
        text = re.sub(r'^\d+\.\s+', '', line.strip())
        story.append(Paragraph(f"• {text}", normal_style)) # Numaralı listeleri de madde imli yap
        i += 1
    elif line.strip().startswith('!['): # Görüntüleri işle
        alt_text_match = re.search(r'\[(.*?)\]', line)
        path_match = re.search(r'\((.*?)\)', line)
        if alt_text_match and path_match:
            story.append(Paragraph(f"<i>{alt_text_match.group(1)}</i>", normal_style))
        i += 1
    else:
        text = line.strip()
        if text:
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # Kalın
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)      # İtalik
            text = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', text)  # Satır içi kod
            story.append(Paragraph(text, normal_style))
        i += 1

# Belgeyi oluştur
try:
    doc.build(story)
    print(f"✓ PDF başarıyla oluşturuldu!")
    print(f"📄 Dosya: {pdf_path.absolute()}")
    theme_desc = "🖨️ Yazıcı dostu (açık tema)" if THEME == "print" else "💻 Ekran (koyu tema)"
    print(f"🎨 Tema: {theme_desc}")
except Exception as e:
    print(f"❌ PDF oluşturulurken bir hata oluştu: {e}")
    print("Lütfen 'DejaVuSans.ttf' yazı tipinin betikle aynı dizinde olduğundan emin olun veya sisteminizde 'Arial' yazı tipinin yüklü olduğunu doğrulayın.")
