import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.flowables import HRFlowable

# Используем DejaVu шрифты для поддержки кириллицы в Docker
try:
    pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FONT = 'DejaVu'
    FONT_BOLD = 'DejaVu-Bold'
except:
    # Fallback если шрифты не установлены
    FONT = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'


class PDFGenerator:
    PRIMARY = HexColor('#AA141E')
    DARK = HexColor('#1A1A1A')
    GRAY = HexColor('#666666')
    WHITE = HexColor('#FFFFFF')

    def __init__(self, report):
        self.report = report

    def generate(self):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        doc = SimpleDocTemplate(
            temp_file.name,
            pagesize=A4,
            leftMargin=20*mm,
            rightMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'],
            fontName=FONT_BOLD, fontSize=16, textColor=self.DARK,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle', parent=styles['Normal'],
            fontName=FONT, fontSize=9, textColor=self.GRAY,
            spaceAfter=16,
        )
        heading_style = ParagraphStyle(
            'CustomHeading', parent=styles['Heading2'],
            fontName=FONT_BOLD, fontSize=13, textColor=self.PRIMARY,
            spaceBefore=14, spaceAfter=6,
        )
        body_style = ParagraphStyle(
            'CustomBody', parent=styles['Normal'],
            fontName=FONT, fontSize=10, textColor=self.DARK,
            spaceAfter=5,
        )

        # Заголовок
        story.append(Paragraph(self.report.title or 'Без названия', title_style))
        story.append(Paragraph(
            f"Департамент городского имущества г. Москвы | {datetime.now().strftime('%d.%m.%Y')}",
            subtitle_style
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PRIMARY))
        story.append(Spacer(1, 8))

        # Мета
        meta_data = [
            ['Дата:', self.report.created_at.strftime('%d.%m.%Y %H:%M')],
        ]

        meta_table = Table(meta_data, colWidths=[30*mm, 100*mm])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
            ('FONTNAME', (1, 0), (1, -1), FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), self.GRAY),
            ('TEXTCOLOR', (1, 0), (1, -1), self.DARK),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PRIMARY))
        story.append(Spacer(1, 8))

        # Контент
        if self.report.data:
            if isinstance(self.report.data, dict):
                data = self.report.data
                if 'content' in data:
                    story.append(Paragraph(data['content'], body_style))
                if 'slides' in data:
                    for slide in data['slides']:
                        # Заголовок слайда
                        if 'heading' in slide:
                            story.append(Paragraph(slide['heading'], heading_style))
                        
                        # Элементы слайда
                        for element in slide.get('elements', []):
                            t = element.get('type')
                            text = element.get('content', '')
                            
                            if t in ('heading', 'title', 'subtitle') and text:
                                story.append(Paragraph(text, heading_style))
                            elif t == 'text' and text:
                                story.append(Paragraph(text, body_style))
                            elif t == 'chart':
                                # Обработка графика - создаем таблицу с данными
                                chart_data = element.get('data', {})
                                categories = chart_data.get('categories', [])
                                values = chart_data.get('values', [])
                                
                                if categories and values:
                                    story.append(Paragraph(element.get('title', 'График'), heading_style))
                                    
                                    # Создаем таблицу с данными графика
                                    table_data = [['Район', 'Значение']]
                                    for cat, val in zip(categories, values):
                                        table_data.append([cat, str(val)])
                                    
                                    table = Table(table_data, colWidths=[60*mm, 30*mm])
                                    table.setStyle(TableStyle([
                                        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
                                        ('FONTNAME', (0, 1), (-1, -1), FONT),
                                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                                        ('TEXTCOLOR', (0, 0), (-1, 0), self.WHITE),
                                        ('TEXTCOLOR', (0, 1), (-1, -1), self.DARK),
                                        ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
                                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                                    ]))
                                    story.append(table)
                                    story.append(Spacer(1, 6))
                
                if 'description' in data:
                    story.append(Paragraph(data['description'], body_style))
            elif isinstance(self.report.data, str):
                story.append(Paragraph(self.report.data, body_style))
        else:
            story.append(Paragraph('Нет данных для отображения', body_style))

        # Подвал
        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PRIMARY))
        story.append(Paragraph(
            f"ДГИ | Отчёт №{self.report.id} | {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            ParagraphStyle('Footer', parent=body_style, fontSize=7, textColor=self.GRAY)
        ))

        doc.build(story)
        return temp_file.name