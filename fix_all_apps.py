import os

print("🔧 STARTE FINALE REPARATUR DER PROGRAMME...")

# ==============================================================================
# 1. coolmath_pro.py (MIT INTELLIGENTER SICHERUNG)
# ==============================================================================
code_math = r'''
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import base64
import os
import tempfile
from fpdf import FPDF
from datetime import datetime

# --- INTELLIGENTE KONFIGURATION ---
# Versucht die Config zu setzen. Wenn das Dashboard schon läuft, passiert nichts.
try:
    st.set_page_config(page_title="°coolMath Pro", layout="wide")
except:
    pass

# --- DESIGN ---
COLOR_BLUE = "#36A9E1"
COLOR_DARK = "#1E3D59"

# CSS laden (verhindert Flackern)
st.markdown(f"""<style>
    .stApp {{ background-color: white; }}
    h1 {{ color: {COLOR_BLUE} !important; }}
    div[data-testid="stMetric"] {{ background-color: {COLOR_DARK}; color: white; border-radius: 8px; padding: 10px; }}
    div[data-testid="stMetric"] label {{ color: #ddd !important; }}
    div[data-testid="stMetricValue"] {{ color: white !important; }}
    div.stButton > button {{ background-color: {COLOR_BLUE} !important; color: white !important; border: none; font-weight: bold; width: 100%; }}
    </style>""", unsafe_allow_html=True)

# --- DATEN ---
SOLAR = {'N': 150, 'NO': 420, 'O': 580, 'SO': 650, 'S': 680, 'SW': 650, 'W': 580, 'NW': 420, 'Dach': 800}
PEAK_HOURS = {'N': 12, 'NO': 9, 'O': 8, 'SO': 10, 'S': 13, 'SW': 15, 'W': 17, 'NW': 18, 'Dach': 13}
U_VALS = {"Altbau": {'w': 1.4, 'f': 2.8}, "Neubau": {'w': 0.28, 'f': 0.9}}
SHADE = {"Keine": 1.0, "Jalousie": 0.25}
PROFILES = {"Wohnen": 200, "Büro": 300}

class Calc:
    def __init__(self, name, area, win, ori, load):
        self.name = name; self.area = area; self.win = win; self.ori = ori; self.load = load
    def run(self):
        res = (self.area * 60) + (self.win * SOLAR[self.ori] * 0.5) + self.load
        return {"Raum": self.name, "Recknagel": res, "VDI_Alt": res*1.1, "Kaltluftsee": res*0.8}
    def curve(self, mx):
        h = np.arange(24); pk = PEAK_HOURS[self.ori]
        return (np.ones(24)*0.4 + np.exp(-((h-pk)**2)/10)*0.6) * mx

# --- UI ---
st.markdown(f"<h1>°coolMath <span style='font-size:0.6em;color:#777'>Pro</span></h1>", unsafe_allow_html=True)
st.divider()

c_sb = st.sidebar
c_sb.header("Parameter")
n_rooms = st.number_input("Anzahl Räume", 1, 5, 1)

rooms = []
tabs = st.tabs([f"Raum {i+1}" for i in range(n_rooms)])

for i, t in enumerate(tabs):
    with t:
        c1, c2 = st.columns(2)
        nm = c1.text_input("Name", f"Raum {i+1}", key=f"n{i}")
        ar = c2.number_input("m²", 10.0, 100.0, 20.0, key=f"a{i}")
        wi = c1.number_input("Fenster m²", 0.0, 20.0, 2.0, key=f"w{i}")
        or_ = c2.selectbox("Ausrichtung", list(SOLAR.keys()), key=f"o{i}")
        us = c1.selectbox("Nutzung", list(PROFILES.keys()), key=f"u{i}")
        rooms.append(Calc(nm, ar, wi, or_, PROFILES[us]))

st.markdown("<br>", unsafe_allow_html=True)
if st.button("BERECHNUNG STARTEN"):
    res = []; tot = 0; curv = np.zeros(24)
    for r in rooms:
        d = r.run(); res.append(d); tot += d['Recknagel']; curv += r.curve(d['Recknagel'])
    
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("Gesamtlast", f"{tot/1000:.2f} kW")
    m2.metric("Simultan", f"{np.max(curv)/1000:.2f} kW")
    
    # Fix für DataFrame Breite
    st.dataframe(pd.DataFrame(res).style.format(precision=0), use_container_width=True)
    
    fig, ax = plt.subplots(figsize=(10,3))
    ax.plot(curv, color=COLOR_BLUE)
    ax.set_title("Lastgang")
    st.pyplot(fig)
'''

# ==============================================================================
# 2. coolTEC.py (MIT INTELLIGENTER SICHERUNG)
# ==============================================================================
code_tec = r'''
import streamlit as st

# --- INTELLIGENTE KONFIGURATION ---
try:
    st.set_page_config(page_title="°coolTEC", layout="wide")
except:
    pass

st.markdown("""<style>
    .stApp {background-color: white;} 
    h1 {color:#36A9E1;} 
    div[data-testid="stMetric"] {background-color:#1E3D59; color:white; border-radius:8px; padding:10px;} 
    label {color:white !important;} 
    div[data-testid="stMetricValue"] {color:white !important;}
    </style>""", unsafe_allow_html=True)

st.markdown("<h1>°coolTEC <span style='font-size:0.6em;color:#777'>Kühlraum</span></h1>", unsafe_allow_html=True)
st.divider()

c1, c2 = st.columns(2)
with c1:
    l = st.number_input("Länge (m)", 1.0, 20.0, 2.5)
    b = st.number_input("Breite (m)", 1.0, 20.0, 2.0)
    h = st.number_input("Höhe (m)", 1.8, 5.0, 2.2)
    vol = l*b*h
    st.info(f"Volumen: {vol:.2f} m³")

with c2:
    typ = st.selectbox("Typ", ["Normalkühlung (+2°C)", "Tiefkühlung (-18°C)"])
    iso = st.selectbox("Isolierung", ["60mm", "80mm", "100mm", "120mm"])
    usage = st.slider("Warenlast Faktor", 0.8, 1.5, 1.0)

is_tk = "Tief" in typ
w_m3 = 85 if not is_tk else 120
last = vol * w_m3 * usage

st.divider()
st.subheader("Auslegung")
m1, m2 = st.columns(2)
m1.metric("Kälteleistung", f"{last:.0f} W", f"{last/1000:.2f} kW")
m2.metric("Raumtemperatur", "-18°C" if is_tk else "+2°C")
'''

# ==============================================================================
# 3. coolFLOW.py (MIT INTELLIGENTER SICHERUNG)
# ==============================================================================
code_flow = r'''
import streamlit as st
import math

# --- INTELLIGENTE KONFIGURATION ---
try:
    st.set_page_config(page_title="°coolFLOW", layout="wide")
except:
    pass

st.markdown("""<style>
    .stApp {background-color: white;} 
    h1 {color:#36A9E1;} 
    div[data-testid="stMetric"] {background-color:#1E3D59; color:white; border-radius:8px; padding:10px;} 
    label {color:white !important;} 
    div[data-testid="stMetricValue"] {color:white !important;}
    </style>""", unsafe_allow_html=True)

st.markdown("<h1>°coolFLOW <span style='font-size:0.6em;color:#777'>Hydraulik</span></h1>", unsafe_allow_html=True)
st.divider()

c1, c2, c3 = st.columns(3)
kw = c1.number_input("Leistung (kW)", 1.0, 2000.0, 50.0)
dt = c2.number_input("Delta T (K)", 2.0, 20.0, 6.0)
dn = c3.number_input("Rohr Innen-Ø (mm)", 10.0, 500.0, 40.0)

m_dot = kw / (4.18 * dt) 
v_dot = m_dot * 3.6 
a = math.pi * ((dn/1000)/2)**2
vel = (v_dot/3600) / a

st.divider()
st.subheader("Ergebnis")
m1, m2, m3 = st.columns(3)
m1.metric("Volumenstrom", f"{v_dot:.2f} m³/h")
m2.metric("Geschwindigkeit", f"{vel:.2f} m/s")
msg = "OK" if 0.5 < vel < 1.5 else "Warnung"
m3.metric("Status", msg)
'''

# ==============================================================================
# 4. DAS DASHBOARD (Robuste Ladefunktion)
# ==============================================================================
code_dash = r'''
import streamlit as st
import os
import base64
from datetime import datetime

# CONFIG MUSS HIER SEIN
st.set_page_config(page_title="Test Dash_board", layout="wide")

def main():
    BG_COLOR = "#36A9E1"
    TEXT_GRAY = "#3C3C3B"
    VERSION = "4.8.0"
    
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG_COLOR}; }}
    .cs-welcome {{ font-size: 34px !important; text-align: center; color: {TEXT_GRAY} !important; margin-top: -50px !important; }}
    div[data-baseweb="select"] {{ background-color: white !important; border-radius: 12px !important; }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="cs-welcome">Willkommen im Cockpit der</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if os.path.exists("Coolsulting_Logo_ohneHG_outlines_weiß.png"):
            st.image("Coolsulting_Logo_ohneHG_outlines_weiß.png", use_container_width=True)
        else:
            st.markdown(f"<h1 style='text-align:center; color:white;'>COOLSULTING</h1>", unsafe_allow_html=True)

    st.markdown("---")

    # --- MENU ---
    tool_wahl = st.selectbox("Anwendung auswählen:", 
                             ["°Übersicht", 
                              "°coolMath Pro (Neu)",
                              "°coolTEC (Kühlraum)",    
                              "°coolFLOW (Hydraulik)",  
                              "°coolSEARCH 4.1",
                              "°coolMATH 3.9",
                              "°coolEngine PRO",
                              "°coolQUOTE PRO 2.1",
                              "°Heizlast WP", 
                              "°WP Quick-Kalkulator"])

    # --- ROUTER ---
    if tool_wahl == "°Übersicht":
        st.info(f"System Version {VERSION} bereit.")
    
    elif tool_wahl == "°coolMath Pro (Neu)":
        run_app_safe("coolmath_pro.py")

    elif tool_wahl == "°coolTEC (Kühlraum)":       
        run_app_safe("coolTEC.py")       

    elif tool_wahl == "°coolFLOW (Hydraulik)":     
        run_app_safe("coolFLOW.py")      

    elif tool_wahl == "°coolSEARCH 4.1":
        run_app_safe("coolSEARCH_4.1.py")
    elif tool_wahl == "°coolMATH 3.9":
        run_app_safe("coolMATH.py")
    elif tool_wahl == "°coolEngine PRO":
        run_app_safe("coolEngine.py")
    elif tool_wahl == "°coolQUOTE PRO 2.1":
        run_app_safe("coolQUOTE_PRO_Modul_2.1.py")
    elif tool_wahl == "°Heizlast WP":
        run_app_safe("Waermepumpen_Auslegung.py")
    elif tool_wahl == "°WP Quick-Kalkulator":
        run_app_safe("WP_Quick_Kalkulator.py")

def run_app_safe(file_path):
    if not os.path.exists(file_path):
        st.error(f"❌ Datei '{file_path}' fehlt im Ordner!")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        
        # JETZT FÜHREN WIR DEN CODE EINFACH AUS
        # Da die Apps jetzt 'try-except' um die Config haben,
        # müssen wir hier nichts mehr manipulieren!
        exec(code, globals())
        
    except Exception as e:
        st.error(f"Fehler beim Starten von {file_path}:")
        st.code(str(e))

if __name__ == '__main__':
    main()
'''

# SCHREIBEN
def save(name, content):
    with open(name, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Erstellt: {name}")

save("Test_Dash_board.py", code_dash)
save("coolmath_pro.py", code_math)
save("coolTEC.py", code_tec)
save("coolFLOW.py", code_flow)

print("\n🎉 FERTIG! Starten Sie jetzt: streamlit run Test_Dash_board.py")
