# -*- coding: utf-8 -*-
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

def fix_formulas_and_tables():
    print("Форматирование формул в 3 РАЗДЕЛ ОТДЕЛЬНО [NF5TGQ]_patched.docx...")
    doc = Document(r"d:\api\3 РАЗДЕЛ ОТДЕЛЬНО [NF5TGQ]_patched.docx")
    
    # Будем искать старые формулы по ключевым словам и заменять их на красиво оформленные абзацы по ГОСТу.
    # Шаблон ГОСТ: Формула по центру, номер формулы (1), (2) ... справа.
    # В Word это делается через табуляцию или специальный абзац. Мы сделаем красивое выравнивание.
    
    for p in doc.paragraphs:
        # 1. Формула ФОТ
        if "ФОТ = " in p.text and "Σ" in p.text:
            p.text = "ФОТ = Σ (Tᵢ × Rᵢ)                                                                                                              (3.1)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
        # 2. Формула CAPEX
        if "CAPEX =" in p.text and "лиц" in p.text:
            p.text = "CAPEX = C_ФОТ + C_лиц + C_обор + C_резерв                                                                           (3.2)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
        # 3. Формула OPEX
        if "OPEX = " in p.text and "обслуж" in p.text:
            p.text = "OPEX = C_обслуж + C_админ + C_подп + C_обуч                                                                        (3.3)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 4. Формула Vгод
        if "Vгод = N_total" in p.text:
            p.text = "Vгод = N_total × T_мес × K_экономии × C_час × 12                                                                    (3.4)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
        # 5. Подстановка в Vгод
        if "8 × 50 × 0.25" in p.text:
            p.text = "Vгод = 8 × 50 × 0.25 × 565 × 12 = 678 000 руб.                                                                            (3.5)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 6. Формула EBIT / NP
        if "NP = EBIT – Tax" in p.text:
            p.text = "NP = EBIT – Tax = 258 000 – 0 = 258 000 руб.                                                                           (3.6)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 7. Формула ROS
        if "ROS = " in p.text and "NP / Vгод" in p.text:
            p.text = "ROS = (NP / Vгод) × 100% = (258 000 / 678 000) × 100% = 38.05%                                                    (3.7)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 8. Формула Q_ТБУ
        if "QТБУ=" in p.text or "Q_ТБУ =" in p.text:
            p.text = "Q_ТБУ = OPEX / C_час = 420 000 / 565 ≈ 743.36 ч.                                                                       (3.8)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 9. Формула V_ТБУ
        if "VТБУ =" in p.text or "V_ТБУ =" in p.text:
            p.text = "V_ТБУ = Q_ТБУ × C_час = 420 000 руб.                                                                                    (3.9)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 10. Формула PP (Срок окупаемости)
        if "PP = CAPEX / NP" in p.text:
            p.text = "PP = CAPEX / NP = 798 500 / 258 000 ≈ 3.09 года                                                                    (3.10)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # 11. Формула ROI
        if "ROI = " in p.text and "CAPEX" in p.text:
            p.text = "ROI = (NP / CAPEX) × 100% = (258 000 / 798 500) × 100% ≈ 32.31%                                                    (3.11)"
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    doc.save(r"d:\api\3 РАЗДЕЛ ОТДЕЛЬНО [NF5TGQ]_patched.docx")
    print("Формулы успешно выровнены по правому краю с номерами (3.1)-(3.11)!")

if __name__ == "__main__":
    fix_formulas_and_tables()
