# ==========================================
# TURSA DATABASE DIAGNOSTICS
# Prüft Verbindung und zeigt Daten an
# ==========================================

import streamlit as st
import pandas as pd
from datetime import datetime

def diagnose_tursa_connection():
    """
    Prüft Tursa-Verbindung und zeigt Status
    """
    st.markdown("## 🗄️ Tursa Datenbank Diagnose")
    st.markdown("---")
    
    # 1. SECRETS PRÜFEN
    st.markdown("### 1️⃣ Secrets Konfiguration")
    
    turso_url = ""
    turso_token = ""
    
    try:
        turso_url = st.secrets.get("TURSO_URL", "")
        turso_token = st.secrets.get("TURSO_TOKEN", "")
        
        if turso_url and turso_token:
            st.success("✅ Tursa Secrets gefunden")
            st.code(f"""
TURSO_URL: {turso_url[:50]}...
TURSO_TOKEN: {turso_token[:20]}... (length: {len(turso_token)})
            """)
        else:
            st.error("❌ Tursa Secrets fehlen!")
            st.warning("Die App verwendet jetzt lokale SQLite-Datenbank im temp-Verzeichnis!")
            
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Secrets: {e}")
        st.warning("Stelle sicher, dass .streamlit/secrets.toml existiert")
    
    st.markdown("---")
    
    # 2. VERBINDUNGSTEST
    st.markdown("### 2️⃣ Verbindungstest")
    
    if st.button("🔌 Tursa Verbindung testen"):
        if not turso_url or not turso_token:
            st.error("❌ Kann nicht testen - Secrets fehlen")
        else:
            try:
                with st.spinner("Verbinde zu Tursa..."):
                    import libsql_experimental as libsql
                    conn = libsql.connect(database=turso_url, auth_token=turso_token)
                    
                    # Test Query
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 as test")
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result and result[0] == 1:
                        st.success("✅ Tursa Verbindung erfolgreich!")
                    else:
                        st.error("❌ Unerwartetes Ergebnis")
                        
            except Exception as e:
                st.error(f"❌ Verbindungsfehler: {e}")
                st.code(f"Details: {type(e).__name__}: {str(e)}")
    
    st.markdown("---")
    
    # 3. TABELLEN PRÜFEN
    st.markdown("### 3️⃣ Tabellen-Status")
    
    if st.button("📊 Tabellen anzeigen"):
        conn, mode = _get_connection_with_mode()
        
        st.info(f"Verbindungstyp: **{mode.upper()}**")
        
        try:
            # Tabellen auflisten
            if mode == "turso":
                query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            else:
                query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            
            cursor = conn.cursor()
            cursor.execute(query)
            tables = cursor.fetchall()
            
            if tables:
                st.success(f"✅ {len(tables)} Tabellen gefunden:")
                for table in tables:
                    st.write(f"- `{table[0]}`")
            else:
                st.warning("⚠️ Keine Tabellen gefunden - Datenbank leer?")
            
            conn.close()
            
        except Exception as e:
            st.error(f"❌ Fehler: {e}")
    
    st.markdown("---")
    
    # 4. DATEN ANZEIGEN
    st.markdown("### 4️⃣ Gespeicherte Angebote")
    
    if st.button("📋 Angebote laden"):
        conn, mode = _get_connection_with_mode()
        
        try:
            # Angebote zählen
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM angebote")
            count = cursor.fetchone()[0]
            
            st.info(f"**{count} Angebote** in Datenbank ({mode.upper()})")
            
            if count > 0:
                # Letzte 10 Angebote
                cursor.execute("""
                    SELECT angebots_nr, kunde_name, kunde_projekt, 
                           erstellt_am, summe_brutto, status
                    FROM angebote 
                    ORDER BY erstellt_am DESC 
                    LIMIT 10
                """)
                
                rows = cursor.fetchall()
                
                df = pd.DataFrame(rows, columns=[
                    'Angebots-Nr', 'Kunde', 'Projekt', 
                    'Datum', 'Summe (€)', 'Status'
                ])
                
                st.dataframe(df, use_container_width=True)
                
                # Statistik
                cursor.execute("""
                    SELECT 
                        COUNT(*) as anzahl,
                        SUM(summe_brutto) as gesamt,
                        AVG(summe_brutto) as durchschnitt
                    FROM angebote
                """)
                
                stats = cursor.fetchone()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Gesamt Angebote", f"{stats[0]}")
                with col2:
                    st.metric("Gesamtvolumen", f"{stats[1]:,.2f} €")
                with col3:
                    st.metric("Durchschnitt", f"{stats[2]:,.2f} €")
            
            conn.close()
            
        except Exception as e:
            st.error(f"❌ Fehler beim Laden: {e}")
            st.code(f"Details: {type(e).__name__}: {str(e)}")
    
    st.markdown("---")
    
    # 5. MIGRATION
    st.markdown("### 5️⃣ Daten-Migration")
    
    st.warning("""
    **⚠️ Vorsicht:** Wenn Daten in lokaler SQLite liegen, 
    müssen sie nach Tursa migriert werden!
    """)
    
    if st.button("🔄 Migration durchführen (SQLite → Tursa)"):
        st.info("Diese Funktion ist noch in Entwicklung.")
        st.markdown("""
        **Manuelle Migration:**
        1. Lokale DB exportieren: `sqlite3 coolmatch_database.db .dump > backup.sql`
        2. In Tursa importieren mit Tursa CLI
        3. Secrets prüfen
        4. App neu starten
        """)


def _get_connection_with_mode():
    """
    Hilfsfunktion: Gibt Connection und Modus zurück
    """
    try:
        turso_url = st.secrets.get("TURSO_URL", "")
        turso_token = st.secrets.get("TURSO_TOKEN", "")
    except:
        turso_url = ""
        turso_token = ""

    if turso_url and turso_token:
        import libsql_experimental as libsql
        conn = libsql.connect(database=turso_url, auth_token=turso_token)
        return conn, "turso"
    else:
        import sqlite3
        import os
        import tempfile
        data_dir = os.path.join(tempfile.gettempdir(), "coolmatch_data")
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "coolmatch_database.db")
        conn = sqlite3.connect(db_path)
        
        st.warning(f"⚠️ Lokale SQLite: `{db_path}`")
        
        return conn, "sqlite"


# In coolMATCH_v7.py einfügen:
def render_database_diagnostics():
    """
    Kann in Sidebar unter app_mode hinzugefügt werden
    """
    diagnose_tursa_connection()


if __name__ == "__main__":
    # Standalone Test
    st.set_page_config(page_title="Tursa Diagnose", layout="wide")
    diagnose_tursa_connection()
