import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
import requests
import json
from datetime import datetime
import io

# --- 1. KONFIGURATION ---
COLOR_BLUE = (54, 169, 225)
COLOR_TEXT_RGB = (60, 60, 59)
LOGO_PATH = "Coolsulting_Logo_ohneHG_outlines_weiß.png"

# MONDAY IDS
COL_ID_DATE    = "date_mknqdvj8"
COL_ID_FILE    = "file_mkngj4yq"
COL_ID_WERT    = "numeric_mknst7mm"
COL_ID_PARTNER = "dropdown_mknagc5a"
COL_ID_PLZ     = "text_mkn9v26m"

# --- 2. HELPER FUNKTIONEN ---

def safe_text(text):
    if not isinstance(text, str): text = str(text)
    replacements = {"€": "EUR", "°": " ", "„": '"', "“": '"', "–": "-", "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    for k, v in replacements.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

def send_to_monday_secure(item_name, pdf_bytes, filename, price_netto, partner, plz):
    try:
        api_key = st.secrets.get("monday_key")
        board_id = st.secrets.get("monday_board_id")
        if not api_key: return False, "API Key fehlt"

        url = "https://api.monday.com/v2"
        headers = {"Authorization": api_key}

        # WICHTIG: Sendet NETTO-PREIS an Monday
        col_vals = json.dumps({
            COL_ID_WERT: str(round(price_netto, 2)),
            COL_ID_PARTNER: str(partner),
            COL_ID_PLZ: str(plz),
            COL_ID_DATE: datetime.now().strftime("%Y-%m-%d"),
            "status": "Angebot"
        })

        query_item = 'mutation ($boardId: ID!, $name: String!, $values: JSON!) { create_item (board_id: $boardId, item_name: $name, column_values: $values) { id } }'
        r1 = requests.post(url, json={'query': query_item, 'variables': {'boardId': int(board_id), 'name': item_name, 'values': col_vals}}, headers=headers)
        
        if "data" not in r1.json(): return False, f"Item Error: {r1.text}"
        item_id = r1.json()["data"]["create_item"]["id"]

        query_file = 'mutation ($file: File!, $itemId: ID!, $columnId: String!) { add_file_to_column (file: $file, item_id: $itemId, column_id: $columnId) { id } }'
        payload = {'query': query_file, 'map': json.dumps({"image": ["variables.file"]}), 'variables': json.dumps({"itemId": int(item_id), "columnId": COL_ID_FILE})}
        
        files = [('image', (filename, pdf_bytes, 'application/pdf'))]
        requests.post(url + "/file", headers=headers, data=payload, files=files)
        return True, "✅ Upload erfolgreich"
    except Exception as e: return False, str(e)

class AngebotsPDF(FPDF):
    def __init__(self, p_data, c_data):
        super().__init__()
        self.p = p_data; self.c = c_data
    def header(self):
        self.set_fill_color(*COLOR_BLUE); self.rect(0, 0, 210, 40, 'F')
        if os.path.exists(LOGO_PATH): self.image(LOGO_PATH, x=10, y=10, w=50)
        self.set_xy(130, 12); self.set_font('Helvetica', 'B', 18); self.set_text_color(255, 255, 255)
        self.cell(70, 10, "Budget Angebot", 0, 0, 'R'); self.ln(30)
    def footer(self):
        self.set_y(-25); self.set_font('Helvetica', '', 8); self.set_text_color(*COLOR_TEXT_RGB)
        self.set_draw_color(180, 180, 180); self.set_line_width(0.1); self.line(10, self.get_y(), 200, self.get_y())
        footer_text = f"{self.p['firma']} | {self.p['strasse']}, {self.p['ort']} | {self.p['email']}"
        self.cell(0, 5, safe_text(footer_text), 0, 1, 'C')
        self.set_text_color(54, 169, 225); self.cell(0, 5, "Es gelten unsere AGB (Hier klicken)", 0, 0, 'C', link=self.p['agb_link'])

# --- 3. DATA & CART ---
@st.cache_data
def load_data():
    data = {'samsung': None, 'zubehoer': None}
    files = os.listdir(os.getcwd())
    s_files = [f for f in files if "Samsung" in f and "xlsx" in f]
    if s_files: data['samsung'] = pd.read_excel(s_files[0])
    z_files = [f for f in files if "ubeh" in f.lower() and ("xlsx" in f or "xls" in f)]
    if z_files:
        df = pd.read_excel(z_files[0])
        if len(df.columns) >= 5:
            df = df.iloc[:, [0, 1, 4]]
            df.columns = ['Artikel', 'Beschreibung', 'Preis']
            data['zubehoer'] = df
    return data

def add_to_cart(typ, art, bez, mge, prs, rab, note=""):
    pos = (len(st.session_state.cart) + 1) * 10
    st.session_state.cart.append({"Pos": pos, "Typ": typ, "Artikel": str(art).replace('.0',''), "Beschreibung": bez, "Menge": float(mge), "Einzelpreis": float(prs), "Rabatt": float(rab), "Notiz": note})

# --- 4. MAIN APP ---
def main():
    st.set_page_config(page_title="coolMATCH Master", layout="wide")
    
    # SIDEBAR
    with st.sidebar:
        st.image("Coolsulting_Logo_ohneHG_blau.png", width=180)
        mwst_rate = st.number_input("MwSt %", 0.0, 100.0, 20.0)
        global_rab = st.number_input("Std. Rabatt %", 0.0, 100.0, 30.0)
        st.divider()
        p_firma = st.text_input("Firma", "°coolsulting")
        p_name = st.text_input("Bearbeiter", "Michael Schäpers")
        p_strasse = st.text_input("Straße", "Mozartstraße 11"); p_ort = st.text_input("Ort", "4020 Linz")
        p_email = st.text_input("E-Mail", "michael.schaepers@coolsulting.at"); p_agb = st.text_input("AGB Link", "https://www.coolsulting.at/agb")
        st.divider()
        c_name = st.text_input("Kunde", "Familie Muster"); c_nr = st.text_input("Nr", "2026-001"); c_ref = st.text_input("Projekt", "Wohnhaus")

    st.markdown(f"<h1><span style='color:white'>°cool</span><span style='color:#3C3C3B'>MATCH</span></h1>", unsafe_allow_html=True)
    db = load_data()
    if 'cart' not in st.session_state: st.session_state.cart = []

    t1, t2, t3 = st.tabs(["❄️ System", "🔧 Zubehör", "🛒 Abschluss"])

    # TAB 1: SYSTEM (FULL RESTORE V6.4 LOGIC)
    with t1:
        if db['samsung'] is not None:
            cat = st.radio("Typ:", ["RAC", "FJM", "BAC", "DVM"], horizontal=True)
            
            # WICHTIG: VORFILTER
            sub_filter = st.selectbox("Typ-Filter:", ["Alle", "Wandgerät", "Kassette", "Kanal", "Konsole"])
            
            df = db['samsung'][db['samsung']['Artikelgruppe'].str.contains(cat, na=False)]
            if sub_filter != "Alle": 
                df = df[df['Bezeichnung'].str.contains(sub_filter, case=False, na=False)]
            
            # FJM LOGIK (AG + 5 RÄUME)
            if cat == "FJM":
                df_ag = df[df['Bezeichnung'].str.contains("Außengerät|AG", case=False)]
                df_ig = df[~df['Bezeichnung'].str.contains("Außengerät|AG", case=False)]
                
                if not df_ag.empty:
                    s_ag = st.selectbox("Außengerät:", df_ag.index, format_func=lambda x: f"{df_ag.loc[x,'Artikelnummer']} | {df_ag.loc[x,'Bezeichnung']}")
                    if st.button("➕ Außengerät"):
                        r = df_ag.loc[s_ag]; add_to_cart("AG", r['Artikelnummer'], r['Bezeichnung'], 1, r['Listenpreis'], global_rab)
                        st.success("AG hinzugefügt")
                
                # DIE 5 RÄUME (V6.4 LOGIC)
                for i in range(1, 6):
                    if st.checkbox(f"Raum {i}"):
                        s_ig = st.selectbox(f"Gerät Raum {i}:", df_ig.index, key=f"r{i}", format_func=lambda x: f"{df_ig.loc[x,'Artikelnummer']} | {df_ig.loc[x,'Bezeichnung']}")
                        if st.button(f"➕ Raum {i}"):
                            r = df_ig.loc[s_ig]; add_to_cart("IG", r['Artikelnummer'], r['Bezeichnung'], 1, r['Listenpreis'], global_rab, f"Raum {i}")
                            st.toast(f"Raum {i} hinzugefügt")
            
            # ANDERE SYSTEME
            else:
                if not df.empty:
                    sel = st.selectbox("Modell:", df.index, format_func=lambda x: f"{df.loc[x,'Artikelnummer']} | {df.loc[x,'Bezeichnung']}")
                    if st.button("➕ Hinzufügen"):
                        r = df.loc[sel]; add_to_cart(cat, r['Artikelnummer'], r['Bezeichnung'], 1, r['Listenpreis'], global_rab)
                        st.success("Hinzugefügt")

    # TAB 2: ZUBEHÖR
    with t2:
        if db['zubehoer'] is not None:
            dfz = db['zubehoer']
            sz = st.text_input("Suche Zubehör:")
            if sz: dfz = dfz[dfz.astype(str).apply(lambda x: x.str.contains(sz, case=False)).any(axis=1)]
            if not dfz.empty:
                selz = st.selectbox("Artikel:", dfz.index, format_func=lambda x: f"{dfz.loc[x,'Artikel']} | {dfz.loc[x,'Beschreibung']}")
                qty = st.number_input("Menge:", 1.0, step=0.5)
                if st.button("➕ Zubehör"):
                    r = dfz.loc[selz]; add_to_cart("Zub", r['Artikel'], r['Beschreibung'], qty, r['Preis'], 0.0)
                    st.success("Hinzugefügt")

    # TAB 3: ABSCHLUSS
    with t3:
        if st.session_state.cart:
            df_c = pd.DataFrame(st.session_state.cart)
            edited = st.data_editor(df_c, use_container_width=True)
            
            sub_net = sum(r['Menge'] * (r['Einzelpreis'] * (1 - r['Rabatt']/100)) for _, r in edited.iterrows())
            
            # MANUELLE EINGRIFFE
            col1, col2 = st.columns([1.5, 1])
            with col1:
                rab_p = st.number_input("Zusatz-Rabatt %", 0.0)
                rab_e = st.number_input("Zusatz-Rabatt €", 0.0)
                pauschal = st.checkbox("Manuelle Pauschale?")
                hide_p = st.checkbox("Einzelpreise ausblenden?")
                m_brutto = st.number_input("Pauschal-Brutto:", value=float(sub_net*1.2)) if pauschal else 0.0
                txt = st.text_area("Text:", value=f"Für Rückfragen stehen wir gerne zur Verfügung.\n\n{p_name}")

            with col2:
                f_net = m_brutto/(1+mwst_rate/100) if pauschal else (sub_net*(1-rab_p/100))-rab_e
                f_brut = m_brutto if pauschal else f_net*(1+mwst_rate/100)
                st.write(f"Netto: {f_net:,.2f} €")
                st.markdown(f"### Gesamt: {f_brut:,.2f} €")

            if st.button("🚀 PDF & MONDAY"):
                try:
                    pdf = AngebotsPDF({"firma": p_firma, "strasse": p_strasse, "ort": p_ort, "email": p_email, "agb_link": p_agb}, {"name": c_name, "nr": c_nr, "ref": c_ref})
                    pdf.add_page(); pdf.set_font("Helvetica", "", 8); pdf.set_text_color(*COLOR_TEXT_RGB)
                    
                    # HEADER PDF
                    pdf.set_font("Helvetica", "I", 8); pdf.cell(0,5, safe_text(f"{p_firma} | {p_strasse}"), ln=True)
                    pdf.ln(5); pdf.set_font("Helvetica", "B", 11); pdf.cell(0,5, safe_text(c_name), ln=True)
                    pdf.ln(10); pdf.set_font("Helvetica", "B", 12); pdf.cell(0,10, safe_text(f"Angebot: {c_ref}"), ln=True)
                    
                    # TABELLE
                    pdf.set_fill_color(*COLOR_BLUE); pdf.set_text_color(255,255,255)
                    w = [10, 30, 85, 10, 20, 15, 25]
                    for x, t in zip(w, ["Pos", "Art", "Text", "Mge", "Preis", "Rab", "Gesamt"]): pdf.cell(x, 8, t, 1, 0, 'C', 1)
                    pdf.ln(); pdf.set_text_color(*COLOR_TEXT_RGB)
                    
                    for _, r in edited.iterrows():
                        if pdf.get_y() > 250: pdf.add_page()
                        x, y = pdf.get_x(), pdf.get_y()
                        # Multi-Cell für Beschreibung
                        pdf.set_xy(x+40, y); pdf.multi_cell(85, 6, safe_text(str(r['Beschreibung'])), 1, 'L')
                        h = pdf.get_y() - y
                        # Andere Zellen passen sich Höhe an
                        pdf.set_xy(x, y); pdf.cell(10, h, str(int(r['Pos'])), 1)
                        pdf.cell(30, h, safe_text(str(r['Artikel']))[:15], 1) # Truncate Artikel
                        pdf.set_xy(x+125, y); pdf.cell(10, h, str(int(r['Menge'])), 1, 0, 'C')
                        pdf.cell(20, h, "-" if hide_p else f"{r['Einzelpreis']:,.2f}", 1, 0, 'R')
                        pdf.cell(15, h, "-" if hide_p else f"{r['Rabatt']:.0f}", 1, 0, 'C')
                        z_sum = r['Menge'] * r['Einzelpreis'] * (1-r['Rabatt']/100)
                        pdf.cell(25, h, "-" if hide_p else f"{z_sum:,.2f}", 1, 1, 'R')

                    # SUMMEN
                    pdf.ln(5); pdf.set_x(135); pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(30, 6, "Netto:", 0); pdf.cell(30, 6, f"{f_net:,.2f}", 0, 1, 'R')
                    pdf.set_x(135); pdf.cell(30, 6, "Gesamt:", 0); pdf.cell(30, 6, f"{f_brut:,.2f}", 0, 1, 'R')
                    pdf.ln(5); pdf.set_font("Helvetica", "", 9); pdf.multi_cell(0, 5, safe_text(txt))
                    
                    # PDF EXPORT FIX
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    plz_ext = "".join(filter(str.isdigit, p_ort))[:4]

                    ok, msg = send_to_monday_secure(f"AN {c_nr}", pdf_bytes, f"AN_{c_nr}.pdf", f_net, p_firma, plz_ext)
                    if ok: st.success(msg); st.download_button("Download PDF", pdf_bytes, f"AN_{c_nr}.pdf")
                    else: st.error(msg)
                
                except Exception as e: st.error(f"Fehler: {e}")

if __name__ == "__main__": main()