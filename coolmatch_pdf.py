from fpdf import FPDF
import os
from coolmatch_config import *

def safe_text(text):
    if not isinstance(text, str): 
        text = str(text)
    replacements = {
        chr(8364): "EUR",
        chr(176): " ",
        chr(8222): '"',
        chr(8220): '"',
        chr(8211): "-",
        chr(8217): "'",
        chr(228): "ae",
        chr(246): "oe",
        chr(252): "ue",
        chr(223): "ss",
        chr(196): "Ae",
        chr(214): "Oe",
        chr(220): "Ue"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

class AngebotsPDF(FPDF):
    def __init__(self, partner_data, customer_data):
        super().__init__()
        self.partner = partner_data
        self.customer = customer_data

    def header(self):
        self.set_fill_color(*COLOR_BLUE)
        self.rect(0, 0, 210, 40, 'F')
        if os.path.exists(LOGO_WHITE_OUTLINE):
            self.image(LOGO_WHITE_OUTLINE, x=10, y=10, w=50)
        self.set_xy(130, 12)
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(*COLOR_WHITE)
        self.cell(70, 10, "Budget Angebot", 0, 0, 'R')
        self.set_xy(130, 22)
        self.set_font('Helvetica', '', 10)
        self.cell(70, 5, "Klimatisierung & Waermepumpen", 0, 0, 'R')
        self.ln(30)

    def footer(self):
        self.set_y(-25)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*COLOR_DARK_GRAY_RGB)
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.2)
        self.line(10, self.get_y(), 200, self.get_y())
        footer_text = f"{self.partner['firma']} | {self.partner['strasse']}, {self.partner['ort']} | {self.partner['email']} | {self.partner['tel']}"
        self.cell(0, 5, safe_text(footer_text), 0, 1, 'C')
        self.set_text_color(*COLOR_BLUE)
        self.set_font('Helvetica', 'U', 8)
        self.cell(0, 5, "Es gelten unsere AGB (Hier klicken)", 0, 0, 'C', link=self.partner['agb'])

def generate_pdf(calc_df, partner_data, customer_data, financial_data, options, closing_text):
    pdf = AngebotsPDF(partner_data, customer_data)
    pdf.add_page()
    pdf.set_text_color(*COLOR_DARK_GRAY_RGB)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, safe_text(f"{partner_data['firma']} - {partner_data['strasse']} - {partner_data['ort']}"), ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 5, safe_text(customer_data['name']), ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 5, "Oesterreich", ln=True)
    pdf.set_xy(130, 50)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(30, 6, "Datum:", 0)
    pdf.cell(40, 6, customer_data['datum'], 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 6, "Gueltig bis:", 0)
    pdf.cell(40, 6, customer_data['gueltig_bis'], 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 6, "Bearbeiter:", 0)
    pdf.cell(40, 6, safe_text(customer_data['bearbeiter']), 0, 1, 'R')
    pdf.ln(20)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, safe_text(f"Angebot: {customer_data['projekt']}"), ln=True)
    pdf.set_line_width(0.1)
    pdf.set_draw_color(*COLOR_BLUE)
    pdf.set_fill_color(*COLOR_BLUE)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "", 8)
    w_p, w_a, w_t, w_m, w_pr, w_r, w_g = 10, 25, 75, 10, 25, 15, 30
    pdf.cell(w_p, 8, "Pos", 1, 0, 'C', True)
    pdf.cell(w_a, 8, "Art", 1, 0, 'L', True)
    pdf.cell(w_t, 8, "Beschreibung", 1, 0, 'L', True)
    pdf.cell(w_m, 8, "Mge", 1, 0, 'C', True)
    pdf.cell(w_pr, 8, "Listenpr.", 1, 0, 'R', True)
    pdf.cell(w_r, 8, "Rab.", 1, 0, 'C', True)
    pdf.cell(w_g, 8, "Gesamt", 1, 1, 'R', True)
    pdf.set_text_color(*COLOR_DARK_GRAY_RGB)
    pdf.set_font("Helvetica", "", 8)
    for _, row in calc_df.sort_values(by="Pos").iterrows():
        t_pos = str(int(row['Pos']))
        t_art = safe_text(str(row['Artikel'])[:15])
        t_txt = safe_text(str(row['Beschreibung']))
        t_mge = f"{row['Menge']:.0f}"
        if options['hide_prices']:
            t_prc, t_rab, t_ges = "-", "-", "-"
        else:
            t_prc = f"{row['Einzelpreis']:,.2f}"
            t_rab = f"{row['Rabatt']:.0f}%"
            t_ges = f"{row['Gesamt']:,.2f}"
        x_s, y_s = pdf.get_x(), pdf.get_y()
        pdf.set_xy(x_s + w_p + w_a, y_s)
        pdf.multi_cell(w_t, 6, t_txt, 1, 'L')
        y_e = pdf.get_y()
        h_row = y_e - y_s
        pdf.set_xy(x_s, y_s)
        pdf.cell(w_p, h_row, t_pos, 1, 0, 'C')
        pdf.cell(w_a, h_row, t_art, 1, 0, 'L')
        pdf.set_xy(x_s + w_p + w_a + w_t, y_s)
        pdf.cell(w_m, h_row, t_mge, 1, 0, 'C')
        pdf.cell(w_pr, h_row, t_prc, 1, 0, 'R')
        pdf.cell(w_r, h_row, t_rab, 1, 0, 'C')
        pdf.cell(w_g, h_row, t_ges, 1, 1, 'R')
        if pdf.get_y() > 250:
            pdf.add_page()
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(5)
    x_val = 130
    if not options['manual_active']:
        pdf.set_x(x_val)
        pdf.cell(30, 5, "Zwischensumme:", 0)
        pdf.cell(40, 5, f"{financial_data['zwischensumme']:,.2f} EUR", 0, 1, 'R')
        if financial_data['rabatt_proz'] > 0:
            rabatt_proz_wert = financial_data['zwischensumme'] * (financial_data['rabatt_proz'] / 100)
            pdf.set_x(x_val)
            pdf.cell(30, 5, f"Rabatt ({financial_data['rabatt_proz']}%):", 0)
            pdf.cell(40, 5, f"- {rabatt_proz_wert:,.2f} EUR", 0, 1, 'R')
        if financial_data['rabatt_abs'] > 0:
            pdf.set_x(x_val)
            pdf.cell(30, 5, "Rabatt (Pauschal):", 0)
            pdf.cell(40, 5, f"- {financial_data['rabatt_abs']:,.2f} EUR", 0, 1, 'R')
    pdf.set_x(x_val)
    pdf.line(x_val, pdf.get_y()+1, 200, pdf.get_y()+1)
    pdf.ln(2)
    pdf.set_x(x_val)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(30, 6, "Netto:", 0)
    pdf.cell(40, 6, f"{financial_data['netto']:,.2f} EUR", 0, 1, 'R')
    pdf.set_x(x_val)
    pdf.set_font("Helvetica", "", 10)
    mwst_satz = (financial_data['ust'] / financial_data['netto'] * 100) if financial_data['netto'] > 0 else 0
    pdf.cell(30, 6, f"MwSt {mwst_satz:.0f}%:", 0)
    pdf.cell(40, 6, f"{financial_data['ust']:,.2f} EUR", 0, 1, 'R')
    pdf.set_x(x_val)
    pdf.set_font("Helvetica", "B", 12)
    label_total = "Pauschalpreis (brutto):" if options['manual_active'] else "Gesamtbetrag:"
    pdf.cell(30, 10, label_total, 0)
    pdf.cell(40, 10, f"{financial_data['brutto']:,.2f} EUR", 0, 1, 'R')
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 9)
    if pdf.get_y() > 240:
        pdf.add_page()
    pdf.multi_cell(0, 5, safe_text(closing_text))
    return bytes(pdf.output())
