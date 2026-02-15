import os

print("--- STARTE INSTALLATION DER APPS ---")

# ---------------------------------------------------------
# 1. CODE FÜR coolmath_pro.py (Weißes Design)
# ---------------------------------------------------------
code_math_pro = r'''
# ==============================================================================
# APP NAME: °coolMath Pro Simulation
# DATEI: coolmath_pro.py
# VERSION: 4.5 (Final Fix)
# ==============================================================================
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import base64
import os
import tempfile
from fpdf import FPDF

if __name__ == "__main__":
    st.set_page_config(page_title="°coolMath Pro", layout="wide", page_icon="❄️")

COLOR_BLUE_DARK = "#1E3D59"
COLOR_BLUE_LIGHT = "#36A9E1"
COLOR_BG = "#FFFFFF"

def get_base64_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

font_file = "POE Vetica UI.ttf"
font_b64 = get_base64_file(font_file)
font_css = ""
if font_b64:
    font_css = f"@font-face {{ font-family: 'CorporateFont'; src: url('data:font/ttf;base64,{font_b64}') format('truetype'); }} html, body, [class*='css'] {{ font-family: 'CorporateFont', sans-serif !important; }}"

st.markdown(f"""
    <style>
    {font_css}
    .stApp {{ background-color: {COLOR_BG}; }}
    h1 {{ color: {COLOR_BLUE_LIGHT} !important; font-weight: 800; }}
    h3 {{ color: {COLOR_BLUE_DARK} !important; }}
    div[data-testid="stMetric"] {{ background-color: {COLOR_BLUE_DARK}; border-radius: 8px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    div[data-testid="stMetric"] label {{ color: rgba(255,255,255,0.8) !important; }}
    div[data-testid="stMetricValue"] {{ color: #ffffff !important; font-size: 28px !important; }}
    div.stButton > button {{ background-color: {COLOR_BLUE_LIGHT} !important; color: white !important; border: none; border-radius: 4px; padding: 0.5rem 1rem; font-weight: bold; }}
    div.stButton > button:hover {{ background-color: {COLOR_BLUE_DARK} !important; }}
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{ background-color: #F8F9FA !important; border: 1px solid #E0E0E0; }}
    </style>
""", unsafe_allow_html=True)

SOLAR_GAIN = {'N': 150, 'NO': 420, 'O': 580, 'SO': 650, 'S': 680, 'SW': 650, 'W': 580, 'NW': 420, 'Dach': 800}
PEAK_HOURS = {'N': 12, 'NO': 9, 'O': 8, 'SO': 10, 'S': 13, 'SW': 15, 'W': 17, 'NW': 18, 'Dach': 13}
U_WERTE = {"Altbau (vor 1980)": {'wand': 1.4, 'fenster': 2.8}, "Bestand (Teilsaniert)": {'wand': 0.8, 'fenster': 1.6}, "Neubau (GEG)": {'wand': 0.28, 'fenster': 0.9}, "Passivhaus": {'wand': 0.15, 'fenster': 0.7}}
SHADING = {"Keine": 1.0, "Innenrollo": 0.65, "Raffstore (Außen)": 0.25, "Markise": 0.15, "Sonnenschutzglas": 0.40}
USAGE_PROFILES = {"Wohnzimmer": 310, "Schlafzimmer": 180, "Büro": 330, "Server": 1000, "Küche": 480}

class RoomCalculation:
    def __init__(self, name, area, height, win_area, ori, b_type, shade, usage_watt, delta_t):
        self.name = name; self.area = area; self.vol = area * height; self.win = win_area; self.ori = ori
        self.u_w = U_WERTE[b_type]['wand']; self.u_f = U_WERTE[b_type]['fenster']; self.shade = SHADING[shade]
        self.load_int = usage_watt; self.dt = delta_t; self.wall_net = max(0, ((area**0.5)*height) - win_area)
    def calc(self):
        q_t = (self.wall_net * self.u_w * self.dt) + (self.win * self.u_f * self.dt)
        q_s = self.win * SOLAR_GAIN[self.ori] * self.shade
        q_v = self.vol * 0.5 * 0.34 * self.dt
        res_reck = q_t + q_s + q_v + self.load_int
        res_vdi_alt = res_reck * 1.15
        vol_lake = self.area * 1.8
        q_t_lake = (self.wall_net * self.u_w * self.dt * 0.3) + (self.win * self.u_f * self.dt)
        q_v_lake = vol_lake * 0.3 * 0.34 * (self.dt - 2)
        res_lake = q_t_lake + (q_s * 0.85) + q_v_lake + self.load_int
        return {"Raum": self.name, "Recknagel": res_reck, "VDI_Alt": res_vdi_alt, "Kaltluftsee": res_lake}
    def get_curve(self, max_load):
        h = np.arange(24); peak = PEAK_HOURS[self.ori]
        solar = np.exp(-((h - peak)**2) / (2 * 2.5**2))
        return (np.ones(24) * 0.4 + (solar * 0.6)) * max_load

class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14); self.set_text_color(54, 169, 225)
        self.cell(0, 10, 'Coolsulting Report', 0, 1); self.line(10, 20, 200, 20); self.ln(5)

def create_pdf(df, total, simultan, chart_path):
    pdf = PDFReport(); pdf.add_page(); pdf.set_font('Helvetica', '', 11); pdf.set_text_color(0,0,0)
    pdf.cell(0, 10, f"Erstellt am: {datetime.now().strftime('%d.%m.%Y')}", 0, 1); pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"Summenlast (Max): {total/1000:.2f} kW", 1, 1, 'L', 1)
    pdf.cell(0, 10, f"Simultanlast (Real): {simultan/1000:.2f} kW", 1, 1, 'L', 1); pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 10); col_w = [50, 35, 35, 35]; head = ["Raum", "Recknagel", "VDI Alt", "Kaltluft"]
    for i, h in enumerate(head): pdf.cell(col_w[i], 8, h, 1)
    pdf.ln(); pdf.set_font('Helvetica', '', 10)
    for _, row in df.iterrows():
        pdf.cell(col_w[0], 8, str(row['Raum']), 1); pdf.cell(col_w[1], 8, f"{row['Recknagel']:.0f} W", 1)
        pdf.cell(col_w[2], 8, f"{row['VDI_Alt']:.0f} W", 1); pdf.cell(col_w[3], 8, f"{row['Kaltluftsee']:.0f} W", 1); pdf.ln()
    if chart_path and os.path.exists(chart_path): pdf.ln(10); pdf.image(chart_path, x=10, w=180)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: return f.read()

st.markdown(f"<h1>°coolMath <span style='font-size:0.6em; color:#777'>Pro Simulation</span></h1>", unsafe_allow_html=True)
st.markdown(f"<div style='text-align:right; margin-top:-40px; color:{COLOR_BLUE_LIGHT}'><b>v4.5</b></div>", unsafe_allow_html=True)
st.divider()

with st.sidebar:
    st.header("Einstellungen"); baujahr = st.selectbox("Standard", list(U_WERTE.keys()), index=1); delta_t = st.slider("Delta T (K)", 6, 12, 8)

st.markdown("### 📝 Raumerfassung"); n_rooms = st.number_input("Anzahl Räume", 1, 10, 2); rooms_obj = []
tabs = st.tabs([f"Raum {i+1}" for i in range(n_rooms)])
for i, tab in enumerate(tabs):
    with tab:
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input(f"Name", f"Raum {i+1}", key=f"n{i}"); area = c2.number_input(f"Fläche", 5.0, 200.0, 25.0, key=f"a{i}")
        win = c3.number_input(f"Fenster", 0.0, 50.0, 4.0, key=f"w{i}"); shade = c4.selectbox("Sonnenschutz", list(SHADING.keys()), index=2, key=f"s{i}")
        c5, c6 = st.columns(2)
        usage_key = c5.selectbox("Nutzung", list