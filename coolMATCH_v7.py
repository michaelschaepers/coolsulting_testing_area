
# ==========================================
# DATEI: coolMATCH_v7.py
# VERSION: 7.0
# DATUM: 16.02.2026
# APPNAME: °coolMATCH_Kalkulator
# AUTOR: Michael Schäpers, coolsulting
#
# ÄNDERUNGEN v7.0:
# 1. STRUKTUR: Modulare Architektur (Config, DB, Monday, Analytics, PDF)
# 2. FEATURES: Analytics Dashboard, Angebots-Historie, Monday.com Integration
# 3. DATABASE: SQLite für vollständige Tracking
# 4. UX: Verbesserte Produktsuche, Schnellzugriff
# 5. DESIGN: CI-Design 100% beibehalten (Header, PDF, Farben)
# ==========================================

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# Import eigener Module
from coolmatch_config import *
from coolmatch_database import CoolMatchDatabase
from coolmatch_monday import MondayIntegration, save_quote_to_monday_ui, render_monday_status
from coolmatch_analytics import CoolMatchAnalytics
from coolmatch_pdf import generate_pdf

# ==========================================
# DATA LOADER
# ==========================================
@st.cache_data
def load_product_data():
    """Lädt Samsung und Zubehör Daten"""
    data = {'samsung': None, 'zubehoer': None, 'files_found': []}
    
    try:
        data['files_found'] = os.listdir(os.getcwd())
    except:
        pass

    # Samsung Datei
    samsung_files = [f for f in data['files_found'] 
                     if any(kw in f for kw in SAMSUNG_FILE_KEYWORDS) and 'xlsx' in f]
    if samsung_files:
        try:
            data['samsung'] = pd.read_excel(samsung_files[0], engine='openpyxl')
            data['samsung']['Artikelgruppe'] = data['samsung']['Artikelgruppe'].astype(str)
        except:
            pass

    # Zubehör Datei
    zubehoer_files = [f for f in data['files_found'] 
                      if any(kw in f.lower() for kw in ZUBEHOER_FILE_KEYWORDS) 
                      and ('xls' in f or 'csv' in f)]
    
    if zubehoer_files:
        zf = zubehoer_files[0]
        df_raw = None
        
        try:
            if zf.endswith('.csv'):
                df_raw = pd.read_csv(zf, sep=None, engine='python')
            else:
                df_raw = pd.read_excel(zf, engine='openpyxl')
        except:
            try:
                df_raw = pd.read_csv(zf, sep=None, engine='python')
            except:
                pass

        if df_raw is not None and len(df_raw.columns) >= 5:
            df_z = df_raw.iloc[:, [0, 1, 4]].copy()
            df_z.columns = ['Artikel', 'Beschreibung', 'Preis']
            df_z['Artikel'] = df_z['Artikel'].fillna("-").astype(str).str.replace(r'\.0$', '', regex=True)
            df_z['Beschreibung'] = df_z['Beschreibung'].fillna("")
            
            if df_z['Preis'].dtype == object:
                df_z['Preis'] = df_z['Preis'].astype(str).str.replace(',', '.', regex=False)
            
            df_z['Preis'] = pd.to_numeric(df_z['Preis'], errors='coerce').fillna(0.0)
            data['zubehoer'] = df_z
    
    return data

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def add_to_cart(typ, art_nr, bez, menge, preis, rabatt, note=""):
    """Fügt Position zum Warenkorb hinzu"""
    next_pos = 10
    if st.session_state.cart:
        try:
            max_pos = max([item.get('Pos', 0) for item in st.session_state.cart])
            next_pos = max_pos + 10
        except:
            pass
        
    st.session_state.cart.append({
        "Pos": next_pos,
        "Typ": typ,
        "Artikel": str(art_nr).replace('.0', ''),
        "Beschreibung": bez,
        "Menge": float(menge),
        "Einzelpreis": float(preis),
        "Rabatt": float(rabatt),
        "Notiz": note
    })

def generate_angebots_nr():
    """
    Generiert laufende Angebots-Nummer aus der Datenbank.
    Format: AN-JJJJ-NNNN (z.B. AN-2026-0001)
    FIX: Nummer wird in Session State gecacht → keine Duplikate bei Reruns.
    """
    # Wenn schon eine Nummer für diese Sitzung generiert wurde → dieselbe zurückgeben
    if 'current_angebots_nr' in st.session_state and st.session_state.current_angebots_nr:
        return st.session_state.current_angebots_nr
    try:
        if 'db' in st.session_state and st.session_state.db is not None:
            nr = st.session_state.db.get_next_angebots_nr()
            st.session_state.current_angebots_nr = nr
            return nr
    except Exception:
        pass
    # Fallback
    year = datetime.now().strftime("%Y")
    nr = f"AN-{year}-{datetime.now().strftime('%H%M')}"
    st.session_state.current_angebots_nr = nr
    return nr

def extract_plz(ort_str):
    """Extrahiert PLZ aus Ort-String (z.B. '4020 Linz' -> '4020')"""
    parts = str(ort_str).split()
    if parts and parts[0].isdigit():
        return parts[0]
    return ""

# ==========================================
# MAIN APP
# ==========================================
def main():
    # Page Config (nur wenn standalone)
    if 'page_configured' not in st.session_state:
        st.set_page_config(page_title=f"{APP_NAME} v{APP_VERSION}", layout="wide")
        st.session_state.page_configured = True

    # Session State initialisieren (DB ZUERST - wird von generate_angebots_nr gebraucht!)
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    
    if 'db' not in st.session_state:
        st.session_state.db = CoolMatchDatabase(DB_PATH)
    
    if 'analytics' not in st.session_state:
        st.session_state.analytics = CoolMatchAnalytics(st.session_state.db)
    
    if 'monday' not in st.session_state:
        st.session_state.monday = MondayIntegration()

    # --- SIDEBAR ---
    with st.sidebar:
        # Original-Logo statt blaues Logo
        logo_options = [
            "Coolsulting_Logo_ohneHG_weiß_grau.png",
            "Coolsulting_Logo_ohneHG_blau.png",
            LOGO_BLUE
        ]
        logo_found = None
        for logo in logo_options:
            if os.path.exists(logo):
                logo_found = logo
                break
        
        if logo_found:
            st.image(logo_found, width=180)
        
        st.markdown(f"### {APP_NAME}")
        st.markdown(f"**Version:** {APP_VERSION}")
        st.divider()
        
        # Modus-Auswahl
        app_mode = st.selectbox(
            "Modus wählen:",
            ["📝 Neues Angebot", "📊 Analytics", "📚 Historie"]
        )
        
        st.divider()
        
        # Nur für Angebots-Modus
        if app_mode == "📝 Neues Angebot":
            st.markdown("### ⚙️ Einstellungen")
            mwst_satz = st.number_input("MwSt Satz (%)", 0.0, 100.0, DEFAULT_MWST, step=1.0)
            validity_days = st.number_input("Gültigkeit (Tage)", 1, 365, DEFAULT_VALIDITY_DAYS)
            
            st.divider()
            st.markdown("### 🏷️ Basis-Rabatt")
            global_rabatt = st.number_input("Standard Rabatt (%)", 0.0, 100.0, DEFAULT_RABATT, step=1.0)
            
            if st.button("Auf alle anwenden"):
                if st.session_state.cart:
                    for item in st.session_state.cart:
                        item['Rabatt'] = global_rabatt
                    st.toast("✅ Rabatt aktualisiert!")
                    st.rerun()

            st.divider()
            st.markdown("### 🏢 Partner")
            p_firma = st.text_input("Firma", DEFAULT_PARTNER['firma'])
            p_name = st.text_input("Bearbeiter", DEFAULT_PARTNER['name'])
            p_strasse = st.text_input("Straße", DEFAULT_PARTNER['strasse'])
            p_ort = st.text_input("Ort", DEFAULT_PARTNER['ort'])
            p_email = st.text_input("E-Mail", DEFAULT_PARTNER['email'])
            p_tel = st.text_input("Telefon", DEFAULT_PARTNER['tel'])
            p_agb = st.text_input("Link zu AGB", DEFAULT_PARTNER['agb'])
            
            st.divider()
            st.markdown("### 👤 Kunde")
            c_name = st.text_input("Kunde", "Familie Muster")
            c_ref = st.text_input("Projekt", "Wohnhaus")
            c_nr = st.text_input("Angebots-Nr", generate_angebots_nr())
        
        # Monday Status immer anzeigen
        st.divider()
        render_monday_status()

    # --- MAIN CONTENT ---
    if app_mode == "📝 Neues Angebot":
        render_quote_creator(
            mwst_satz, validity_days, global_rabatt,
            p_firma, p_name, p_strasse, p_ort, p_email, p_tel, p_agb,
            c_name, c_ref, c_nr
        )
    
    elif app_mode == "📊 Analytics":
        st.session_state.analytics.render_dashboard()
    
    elif app_mode == "📚 Historie":
        st.session_state.analytics.render_quote_history()

# ==========================================
# ANGEBOTS-ERSTELLUNG
# ==========================================
def render_quote_creator(mwst, validity, rabatt,
                         p_firma, p_name, p_strasse, p_ort, p_email, p_tel, p_agb,
                         c_name, c_ref, c_nr):
    """Hauptbereich für Angebotserstellung"""
    
    # --- HEADER (CI-KONFORM) ---
    cur_date = datetime.now().strftime('%d.%m.%Y')
    st.markdown(f"""
    <div style='margin-top: 20px; margin-bottom: 20px;'>
        <h1 style='margin: 0; padding: 0; line-height: 1.0; font-family: Helvetica, sans-serif; font-weight: bold;'>
            <span style='color: {COLOR_BLUE_HEX};'>°cool</span><span style='color: {COLOR_DARK_GRAY};'>MATCH_Kalkulator</span>
        </h1>
        <p style='color: {COLOR_DARK_GRAY}; font-size: 12px; margin-top: 5px;'>
            APP Version {APP_VERSION} | {cur_date}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Produktdaten laden
    db = load_product_data()
    
    # Status-Check
    if db['samsung'] is None or db['zubehoer'] is None:
        with st.expander("⚠️ Status", expanded=True):
            if db['samsung'] is None:
                st.error("❌ Samsung Datei fehlt.")
            if db['zubehoer'] is None:
                st.error("❌ Zubehör Datei fehlt.")

    # Closing Text initialisieren
    if 'closing_text' not in st.session_state:
        st.session_state.closing_text = get_closing_text_template(p_name)

    # --- TABS ---
    tab_sys, tab_zub, tab_cart = st.tabs([
        "❄️ System", 
        "🔧 Zubehör+Montage", 
        "🛒 Abschluss"
    ])

    # === TAB 1: SYSTEM ===
    with tab_sys:
        render_system_tab(db['samsung'], rabatt)

    # === TAB 2: ZUBEHÖR ===
    with tab_zub:
        render_zubehoer_tab(db['zubehoer'], rabatt)

    # === TAB 3: WARENKORB ===
    with tab_cart:
        render_cart_tab(mwst, validity, p_firma, p_name, p_strasse, p_ort,
                       p_email, p_tel, p_agb, c_name, c_ref, c_nr)

# ==========================================
# TAB: SYSTEM
# ==========================================
def render_system_tab(df_samsung, default_rabatt):
    """Samsung Systeme auswählen"""
    
    if df_samsung is None:
        st.warning("⚠️ Samsung Datei nicht gefunden")
        return
    
    # System-Auswahl
    sys_cat = st.radio(
        "System:",
        ["Single Split (RAC)", "Multi Split (FJM)", "Gewerbe (BAC)", "DVM (VRF)"],
        horizontal=True
    )
    
    st.divider()
    
    # === SINGLE SPLIT & GEWERBE ===
    if "RAC" in sys_cat or "BAC" in sys_cat:
        key = "S_RAC" if "RAC" in sys_cat else "S_BAC"
        df_filtered = df_samsung[df_samsung['Artikelgruppe'].str.contains(key, na=False, case=False)]
        
        # Suche
        search_txt = st.text_input(f"🔍 Suche {key}:", "")
        if search_txt:
            df_filtered = df_filtered[df_filtered.apply(
                lambda r: search_txt.lower() in str(r).lower(), axis=1
            )]
        
        if not df_filtered.empty:
            sel = st.selectbox(
                "Set auswählen:",
                df_filtered.index,
                format_func=lambda x: f"{df_filtered.loc[x,'Artikelnummer']} | {df_filtered.loc[x,'Bezeichnung']} | {df_filtered.loc[x,'Listenpreis']:.2f}€"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                pass  # Platzhalter
            with col2:
                if st.button("➕ Set hinzufügen", type="primary", use_container_width=True):
                    r = df_filtered.loc[sel]
                    add_to_cart("Set", r['Artikelnummer'], r['Bezeichnung'], 
                               1, r['Listenpreis'], default_rabatt)
                    st.success("✅ Hinzugefügt!")
                    st.rerun()
    
    # === MULTI SPLIT ===
    elif "FJM" in sys_cat:
        st.info("💡 Zuerst Außengerät, dann Innengeräte hinzufügen")
        
        df_fjm = df_samsung[df_samsung['Artikelgruppe'].str.contains("S_FJM", na=False)]
        df_ag = df_fjm[df_fjm['Bezeichnung'].str.contains("Außengerät|AG", case=False)]
        df_ig = df_fjm[~df_fjm.index.isin(df_ag.index)]
        
        # Außengerät
        if not df_ag.empty:
            st.markdown("#### 1️⃣ Außengerät")
            s_ag = st.selectbox(
                "Außengerät:",
                df_ag.index,
                format_func=lambda x: f"{df_ag.loc[x,'Artikelnummer']} | {df_ag.loc[x,'Bezeichnung']} | {df_ag.loc[x,'Listenpreis']:.2f}€"
            )
            
            if st.button("➕ Außengerät hinzufügen", type="primary"):
                r = df_ag.loc[s_ag]
                add_to_cart("AG", r['Artikelnummer'], r['Bezeichnung'],
                           1, r['Listenpreis'], default_rabatt)
                st.toast("✅ AG hinzugefügt!")
                st.rerun()
        
        # Innengeräte
        st.markdown("#### 2️⃣ Innengeräte")
        
        for i in range(1, 6):
            with st.expander(f"Raum {i}"):
                s_ig = st.selectbox(
                    f"Gerät für Raum {i}:",
                    df_ig.index,
                    key=f"ig_select_{i}",
                    format_func=lambda x: f"{df_ig.loc[x,'Artikelnummer']} | {df_ig.loc[x,'Bezeichnung']} | {df_ig.loc[x,'Listenpreis']:.2f}€"
                )
                
                if st.button(f"➕ Raum {i} hinzufügen", key=f"ig_btn_{i}"):
                    r = df_ig.loc[s_ig]
                    add_to_cart("IG", r['Artikelnummer'], r['Bezeichnung'],
                               1, r['Listenpreis'], default_rabatt, f"Raum {i}")
                    st.toast(f"✅ Raum {i} hinzugefügt!")
                    st.rerun()
    
    # === DVM ===
    elif "DVM" in sys_cat:
        search_dvm = st.text_input("🔍 Suche DVM:", "")
        
        if search_dvm:
            df_results = df_samsung[df_samsung.apply(
                lambda r: search_dvm.lower() in str(r).lower(), axis=1
            )]
            
            if not df_results.empty:
                sel = st.selectbox(
                    "Teil:",
                    df_results.index,
                    format_func=lambda x: f"{df_results.loc[x,'Artikelnummer']} | {df_results.loc[x,'Bezeichnung']} | {df_results.loc[x,'Listenpreis']:.2f}€"
                )
                
                if st.button("➕ DVM hinzufügen", type="primary"):
                    r = df_results.loc[sel]
                    add_to_cart("DVM", r['Artikelnummer'], r['Bezeichnung'],
                               1, r['Listenpreis'], default_rabatt)
                    st.success("✅ Hinzugefügt!")
                    st.rerun()

# ==========================================
# TAB: ZUBEHÖR
# ==========================================
def render_zubehoer_tab(df_zubehoer, default_rabatt):
    """Zubehör und Montage"""
    
    if df_zubehoer is None:
        st.warning("⚠️ Zubehör-Datei nicht gefunden")
        return
    
    # Suche
    search_z = st.text_input("🔍 Suche Montage/Zubehör:", "")
    
    df_filtered = df_zubehoer.copy()
    if search_z:
        df_filtered = df_filtered[df_filtered.astype(str).apply(
            lambda x: x.str.contains(search_z, case=False)
        ).any(axis=1)]
    
    if df_filtered.empty:
        st.info("Keine Artikel gefunden")
        return
    
    # Artikel auswählen
    sel_z = st.selectbox(
        "Artikel auswählen:",
        df_filtered.index,
        format_func=lambda x: f"Art.Nr.: {df_filtered.loc[x,'Artikel']} | {df_filtered.loc[x,'Beschreibung'][:60]} | {df_filtered.loc[x,'Preis']:.2f} €"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        qty = st.number_input("Menge:", 1.0, 100.0, 1.0, step=0.5)
    
    with col2:
        st.write(" ")
        st.write(" ")
        
    with col3:
        st.write(" ")
        st.write(" ")
        if st.button("➕ Hinzufügen", type="primary", use_container_width=True):
            r = df_filtered.loc[sel_z]
            add_to_cart("Zubehör", str(r['Artikel']), str(r['Beschreibung']),
                       qty, float(r['Preis']), default_rabatt)
            st.success("✅ Hinzugefügt!")
            st.rerun()

# ==========================================
# TAB: WARENKORB
# ==========================================
def render_cart_tab(mwst, validity, p_firma, p_name, p_strasse, p_ort,
                   p_email, p_tel, p_agb, c_name, c_ref, c_nr):
    """Warenkorb, Berechnung und PDF"""
    
    st.subheader("🛒 Kalkulation & Abschluss")
    
    if not st.session_state.cart:
        st.info("🛒 Warenkorb ist leer. Fügen Sie Produkte hinzu.")
        return
    
    # DataFrame erstellen
    df_cart = pd.DataFrame(st.session_state.cart)
    if "Pos" not in df_cart.columns:
        df_cart["Pos"] = range(10, len(df_cart)*10 + 10, 10)
    if "Rabatt" not in df_cart.columns:
        df_cart["Rabatt"] = 0.0
    
    df_cart = df_cart.sort_values(by="Pos")

    # Data Editor
    edited_df = st.data_editor(
        df_cart,
        num_rows="dynamic",
        use_container_width=True,
        key="cart_editor",
        column_config={
            "Pos": st.column_config.NumberColumn(min_value=1, step=1, format="%d"),
            "Menge": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            "Einzelpreis": st.column_config.NumberColumn(min_value=0.0, format="%.2f €"),
            "Rabatt": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, format="%.1f %%")
        }
    )

    # Berechnungen
    try:
        calc_df = edited_df.copy()
        if "Gesamt" in calc_df.columns:
            calc_df = calc_df.drop(columns=["Gesamt"])
        
        calc_df['Menge'] = pd.to_numeric(calc_df['Menge'], errors='coerce').fillna(0)
        calc_df['Einzelpreis'] = pd.to_numeric(calc_df['Einzelpreis'], errors='coerce').fillna(0)
        calc_df['Rabatt'] = pd.to_numeric(calc_df['Rabatt'], errors='coerce').fillna(0)
        calc_df['Gesamt'] = calc_df['Menge'] * (calc_df['Einzelpreis'] * (1 - calc_df['Rabatt']/100))
        
        # Zurück in Session State
        st.session_state.cart = calc_df.sort_values(by="Pos").to_dict('records')
        
        zwischensumme = calc_df['Gesamt'].sum()

        st.markdown("---")
        
        # Zwei Spalten
        col_L, col_R = st.columns([1.5, 1])
        
        with col_L:
            st.markdown("#### 📝 Abschluss-Text")
            st.session_state.closing_text = st.text_area(
                "Text / AGB / Notizen:",
                value=st.session_state.closing_text,
                height=150
            )
            
            st.markdown("#### ⚙️ Modus")
            manual_active = st.checkbox("Manuelle Pauschale?")
            hide_prices = st.checkbox("Einzelpreise ausblenden?")
            
            manual_brutto = 0.0
            if manual_active:
                manual_brutto = st.number_input(
                    "Pauschalpreis Brutto (€):",
                    0.0, 1000000.0, 0.0, step=100.0
                )

            endrabatt_proz = 0.0
            endrabatt_abs = 0.0
            if not manual_active:
                c1, c2 = st.columns(2)
                with c1:
                    endrabatt_proz = st.number_input("Extra Rabatt %", 0.0, 100.0, 0.0, step=0.5)
                with c2:
                    endrabatt_abs = st.number_input("Extra Rabatt €", 0.0, 10000.0, 0.0, step=10.0)

        with col_R:
            st.markdown("#### 💰 Vorschau")
            
            if manual_active:
                st.markdown(f"**Pauschal (Brutto): {manual_brutto:,.2f} €**")
                netto_final = manual_brutto / (1 + mwst/100)
                ust_wert = manual_brutto - netto_final
                st.write(f"Netto: {netto_final:,.2f} €")
                st.write(f"MwSt: {ust_wert:,.2f} €")
                fin_net = netto_final
                fin_ust = ust_wert
                fin_brut = manual_brutto
            else:
                rab_p = zwischensumme * (endrabatt_proz / 100)
                netto_final = zwischensumme - rab_p - endrabatt_abs
                ust_wert = netto_final * (mwst / 100)
                brutto_final = netto_final + ust_wert
                
                st.write(f"Summe: {zwischensumme:,.2f} €")
                if endrabatt_proz > 0:
                    st.write(f"- {endrabatt_proz}%: {rab_p:,.2f} €")
                if endrabatt_abs > 0:
                    st.write(f"- Pauschal: {endrabatt_abs:,.2f} €")
                st.markdown("---")
                st.write(f"Netto: {netto_final:,.2f} €")
                st.write(f"MwSt {mwst}%: {ust_wert:,.2f} €")
                st.markdown(f"### 💸 Gesamt: {brutto_final:,.2f} €")
                
                fin_net = netto_final
                fin_ust = ust_wert
                fin_brut = brutto_final

        st.markdown("---")
        
        # Buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 PDF Angebot", type="primary", use_container_width=True):
                create_pdf_and_save(
                    calc_df, p_firma, p_name, p_strasse, p_ort, p_email, p_tel, p_agb,
                    c_name, c_ref, c_nr, mwst, validity,
                    zwischensumme, endrabatt_proz, endrabatt_abs,
                    fin_net, fin_ust, fin_brut,
                    manual_active, hide_prices
                )
        
        with col2:
            if st.button("💾 In DB speichern", use_container_width=True):
                save_to_database(
                    c_name, c_ref, c_nr, p_name, p_firma, validity,
                    fin_net, fin_brut, mwst, endrabatt_proz, endrabatt_abs,
                    manual_active, hide_prices, st.session_state.cart
                )
        
        with col3:
            if st.button("🗑️ Korb leeren", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
            
    except Exception as e:
        st.error(f"❌ Fehler: {e}")

# ==========================================
# PDF & SPEICHERN
# ==========================================
# ==========================================
# PDF & SPEICHERN - FIXED VERSION
# ==========================================
def create_pdf_and_save(calc_df, p_firma, p_name, p_strasse, p_ort, p_email, p_tel, p_agb,
                       c_name, c_ref, c_nr, mwst, validity,
                       zwischensumme, rab_proz, rab_abs,
                       netto, ust, brutto, manual_active, hide_prices):
    """
    Erstellt PDF und speichert AUTOMATISCH in DB + Monday.com
    
    ÄNDERUNGEN v7.1:
    - Automatischer DB-Save
    - Automatischer Monday.com Upload mit PDF
    - Keine separaten Buttons mehr nötig
    """
    
    try:
        # Partner & Kunde Daten
        partner_data = {
            'firma': p_firma,
            'strasse': p_strasse,
            'ort': p_ort,
            'email': p_email,
            'tel': p_tel,
            'agb': p_agb
        }
        
        customer_data = {
            'name': c_name,
            'projekt': c_ref,
            'nr': c_nr,
            'datum': datetime.now().strftime("%d.%m.%Y"),
            'gueltig_bis': (datetime.now() + timedelta(days=validity)).strftime("%d.%m.%Y"),
            'bearbeiter': p_name
        }
        
        financial_data = {
            'zwischensumme': zwischensumme,
            'rabatt_proz': rab_proz,
            'rabatt_abs': rab_abs,
            'netto': netto,
            'ust': ust,
            'brutto': brutto
        }
        
        options = {
            'manual_active': manual_active,
            'hide_prices': hide_prices
        }
        
        # PDF generieren
        with st.spinner("📄 Erstelle PDF..."):
            pdf_bytes = generate_pdf(
                calc_df, partner_data, customer_data,
                financial_data, options, st.session_state.closing_text
            )
        
        st.success("✅ PDF erfolgreich erstellt!")
        
        # 1. AUTOMATISCH IN DATENBANK SPEICHERN
        try:
            with st.spinner("💾 Speichere in Datenbank..."):
                valid_until = (datetime.now() + timedelta(days=validity)).strftime("%Y-%m-%d")
                
                quote_header = {
                    'angebots_nr': c_nr,
                    'kunde_name': c_name,
                    'kunde_projekt': c_ref,
                    'kunde_nr': '',
                    'gueltig_bis': valid_until,
                    'bearbeiter': p_name,
                    'firma': p_firma,
                    'summe_netto': netto,
                    'summe_brutto': brutto,
                    'mwst_satz': mwst,
                    'rabatt_prozent': rab_proz,
                    'rabatt_absolut': rab_abs,
                    'manual_preis': manual_active,
                    'preise_verborgen': hide_prices,
                    'status': 'Erstellt',
                    'monday_item_id': '',  # Wird gleich aktualisiert
                    'closing_text': st.session_state.closing_text,
                    'notizen': ''
                }
                
                db = st.session_state.db
                angebots_id = db.save_quote(quote_header, st.session_state.cart)
                
                st.success(f"✅ In Datenbank gespeichert! (ID: {angebots_id})")
        
        except Exception as e:
            st.warning(f"⚠️ DB-Speicherung fehlgeschlagen: {e}")
        
        # 2. AUTOMATISCH IN MONDAY.COM SPEICHERN (wenn konfiguriert)
        monday_item_id = ""
        if st.session_state.monday.is_configured():
            try:
                with st.spinner("📤 Lade zu Monday.com hoch..."):
                    monday_data = {
                        'angebots_nr': c_nr,
                        'datum': datetime.now(),
                        'angebotswert': brutto,  # Brutto-Wert
                        'partner': p_firma,
                        'plz': extract_plz(p_ort),
                        'kunde': c_name  # Für Item Name falls angebots_nr fehlt
                    }
                    
                    # PDF-Dateiname
                    pdf_filename = f"AN_{c_nr.replace('/', '_').replace(' ', '_')}.pdf"
                    
                    # Upload mit PDF
                    success, monday_item_id = st.session_state.monday.save_quote_to_monday(
                        monday_data, 
                        pdf_bytes,
                        pdf_filename
                    )
                    
                    if success:
                        st.success(f"✅ In Monday.com gespeichert! (Item: {monday_item_id})")
                        
                        # Monday Item ID in DB aktualisieren
                        try:
                            db.update_monday_id(c_nr, monday_item_id)
                        except:
                            pass
                    else:
                        st.warning("⚠️ Monday.com Upload fehlgeschlagen (siehe Logs)")
                        # DEBUG: Direkt testen was Monday zurückgibt
                        with st.expander("🔍 Monday.com Debug Info"):
                            import requests, json
                            headers = {
                                "Authorization": st.session_state.monday.api_token,
                                "Content-Type": "application/json"
                            }
                            # Test 1: Verbindung
                            r = requests.post("https://api.monday.com/v2",
                                headers=headers,
                                json={"query": "query { me { name email } }"},
                                timeout=10)
                            st.write("**Verbindungstest:**", r.status_code, r.json())

                            # Test 2: Item mit ALLEN Feldern wie save_quote_to_monday
                            cv_full = {
                                "date_mknqdvj8": {"date": "2026-02-16"},
                                "numeric_mknst7mm": str(round(float(brutto), 2)),
                                "dropdown_mknagc5a": {"labels": [str(p_firma)]},
                                "text_mkn9v26m": extract_plz(p_ort),
                                "color_mkncgyk5": {"label": "Angebot"}
                            }
                            cv_escaped = json.dumps(cv_full).replace("\\", "\\\\").replace('"', '\\"')
                            q_full = f'mutation {{ create_item (board_id: {st.session_state.monday.board_id}, item_name: "DEBUG_FULL_{c_nr}", column_values: "{cv_escaped}") {{ id }} }}'
                            r_full = requests.post("https://api.monday.com/v2",
                                headers=headers,
                                json={"query": q_full},
                                timeout=10)
                            st.write("**Item mit allen Feldern:**", r_full.status_code)
                            st.json(r_full.json())

                            # Test 3: PDF Upload testen (wenn Item erstellt)
                            full_data = r_full.json()
                            if 'data' in full_data and full_data['data'] and 'create_item' in full_data['data']:
                                test_item_id = full_data['data']['create_item']['id']
                                st.write(f"**Item ID:** {test_item_id} → teste PDF Upload...")
                                
                                # Minimales Test-PDF
                                test_pdf = b"%PDF-1.4 test"
                                upload_headers = {"Authorization": st.session_state.monday.api_token}
                                query_upload = '''
                                mutation ($file: File!, $itemId: ID!, $columnId: String!) {
                                    add_file_to_column (file: $file, item_id: $itemId, column_id: $columnId) { id name }
                                }'''
                                variables = {"itemId": int(test_item_id), "columnId": "file_mkngj4yq"}
                                map_data = {"image": ["variables.file"]}
                                files = {
                                    'query': (None, query_upload),
                                    'variables': (None, json.dumps(variables)),
                                    'map': (None, json.dumps(map_data)),
                                    'image': ("test.pdf", test_pdf, 'application/pdf')
                                }
                                r_upload = requests.post(
                                    "https://api.monday.com/v2/file",
                                    headers=upload_headers,
                                    files=files,
                                    timeout=30
                                )
                                st.write("**PDF Upload:**", r_upload.status_code)
                                st.json(r_upload.json())
            
            except Exception as e:
                st.warning(f"⚠️ Monday.com Fehler: {e}")
        else:
            st.info("ℹ️ Monday.com nicht konfiguriert - nur DB-Speicherung")
        
        # 3. PDF DOWNLOAD BUTTON
        st.download_button(
            "⬇️ PDF herunterladen",
            pdf_bytes,
            f"AN_{c_nr.replace('/', '_').replace(' ', '_')}.pdf",
            "application/pdf",
            use_container_width=True,
            key="pdf_download_btn"
        )
        
        # Info-Box
        st.info("""
        **✅ Workflow abgeschlossen:**
        - PDF erstellt
        - In Datenbank gespeichert
        - In Monday.com hochgeladen (inkl. PDF)
        
        Jetzt kannst du das PDF herunterladen oder ein neues Angebot starten.
        """)
        
        # Nummer für nächstes Angebot zurücksetzen
        if 'current_angebots_nr' in st.session_state:
            del st.session_state.current_angebots_nr
        
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        import traceback
        st.code(traceback.format_exc())


def save_to_database(c_name, c_ref, c_nr, bearbeiter, firma, validity,
                    netto, brutto, mwst, rab_proz, rab_abs,
                    manual_active, hide_prices, cart):
    """
    Speichert Angebot in Datenbank (DEPRECATED - wird von create_pdf_and_save erledigt)
    
    Diese Funktion wird nicht mehr direkt aufgerufen, da die DB-Speicherung
    jetzt automatisch beim PDF-Download erfolgt.
    """
    
    try:
        valid_until = (datetime.now() + timedelta(days=validity)).strftime("%Y-%m-%d")
        
        quote_header = {
            'angebots_nr': c_nr,
            'kunde_name': c_name,
            'kunde_projekt': c_ref,
            'kunde_nr': '',
            'gueltig_bis': valid_until,
            'bearbeiter': bearbeiter,
            'firma': firma,
            'summe_netto': netto,
            'summe_brutto': brutto,
            'mwst_satz': mwst,
            'rabatt_prozent': rab_proz,
            'rabatt_absolut': rab_abs,
            'manual_preis': manual_active,
            'preise_verborgen': hide_prices,
            'status': 'Erstellt',
            'monday_item_id': '',
            'closing_text': st.session_state.closing_text,
            'notizen': ''
        }
        
        db = st.session_state.db
        angebots_id = db.save_quote(quote_header, cart)
        
        st.success(f"✅ Angebot gespeichert! (ID: {angebots_id})")
        
    except Exception as e:
        st.error(f"❌ Speicherfehler: {e}")

# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    main()