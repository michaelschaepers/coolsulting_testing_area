# ==========================================
# DATEI: coolmatch_config.py
# VERSION: 7.0
# DATUM: 16.02.2026
# AUTOR: Michael Schäpers, coolsulting
# BESCHREIBUNG: Zentrale Konfiguration für coolMATCH System
# ==========================================

# --- CORPORATE IDENTITY FARBEN ---
COLOR_BLUE = (54, 169, 225)
COLOR_BLUE_HEX = "#36A9E1"
COLOR_DARK_GRAY = "#3C3C3B"
COLOR_DARK_GRAY_RGB = (60, 60, 59)
COLOR_WHITE = (255, 255, 255)

# --- LOGO PFADE ---
LOGO_WHITE_OUTLINE = "Coolsulting_Logo_ohneHG_outlines_weiß.png"
LOGO_BLUE = "Coolsulting_Logo_ohneHG_blau.png"

# --- APP VERSION ---
APP_VERSION = "7.1"
APP_NAME = "°coolMATCH_Kalkulator"

# --- DATENBANK ---
import os

# Datenbank-Pfad (einfache SQLite)
if os.path.exists('/mount/src'):
    # Streamlit Cloud - temporär (geht bei Neustart verloren!)
    DB_PATH = "/tmp/coolmatch_database.db"
else:
    # Lokal - persistent
    DB_PATH = "data/coolmatch_database.db"

# --- MONDAY.COM INTEGRATION ---
MONDAY_API_URL = "https://api.monday.com/v2"
# Diese Werte werden aus st.secrets geladen:
# - MONDAY_API_TOKEN
# - MONDAY_BOARD_ID

MONDAY_COLUMNS = {
    'datum': 'date_mknqdvj8',
    'datei': 'file_mkngj4yq',
    'angebotswert': 'numeric_mknst7mm',
    'partner': 'dropdown_mknagc5a',
    'plz': 'text_mkn9v26m'
}

# --- STANDARD EINSTELLUNGEN ---
DEFAULT_MWST = 20.0
DEFAULT_VALIDITY_DAYS = 7
DEFAULT_RABATT = 30.0

# --- PARTNER DATEN ---
DEFAULT_PARTNER = {
    "firma": "°coolsulting",
    "name": "Michael Schäpers",
    "strasse": "Mozartstraße 11",
    "ort": "4020 Linz",
    "email": "michael.schaepers@coolsulting.at",
    "tel": "+43 676 331 74 14",
    "agb": "https://www.coolsulting.at/agb"
}

# --- PRODUKTDATEIEN ---
# Samsung Preisliste: S_Klima_Artikel_Import_*.xlsx
SAMSUNG_FILE_KEYWORDS = ["S_Klima", "Samsung"]
ZUBEHOER_FILE_KEYWORDS = ["ubeh", "zubeh"]

# --- SAMSUNG KATEGORIEN ---
SYSTEM_TYPES = {
    'RAC': 'Single Split (RAC)',
    'FJM': 'Multi Split (FJM)',
    'BAC': 'Gewerbe (BAC)'
}

# --- F-GASE TEXT ---
FGASE_WARNING = """Gemäß der F-Gase-Verordnung dürfen Arbeiten an Kälte-, Klima- und Wärmepumpenanlagen nur von zertifizierten Kältetechnikern durchgeführt werden. Auftraggeber haften für Verstöße mit Strafen bis zu 50.000 €."""

# --- CLOSING TEXT TEMPLATE ---
def get_closing_text_template(bearbeiter_name):
    return f"""Für Rückfragen stehen wir Ihnen jederzeit gerne zur Verfügung.

Mit freundlichen Grüßen
{bearbeiter_name}

In Bezug auf zusätzliche Produktoptionen und Zusätze gilt, dass nur diejenigen geliefert werden, die explizit im Angebot bzw. in den technischen Daten und dem Angebot beigefügten Aufstellungen aufgeführt sind.

{FGASE_WARNING}"""
