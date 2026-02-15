# ==========================================
# DATEI: coolmatch_monday.py
# VERSION: 7.0
# AUTOR: Michael Schäpers, coolsulting
# BESCHREIBUNG: Monday.com Integration für Angebots-Tracking
# ==========================================

import requests
import json
from datetime import datetime
from typing import Dict, Optional
import streamlit as st

class MondayIntegration:
    """Verwaltet die Kommunikation mit Monday.com"""
    
    def __init__(self, api_token: str = None, board_id: str = None):
        """
        Initialisiert Monday.com Integration
        
        Args:
            api_token: API Token (aus st.secrets wenn None)
            board_id: Board ID (aus st.secrets wenn None)
        """
        self.api_url = "https://api.monday.com/v2"
        
        # Token und Board ID aus Secrets laden
        try:
            self.api_token = api_token or st.secrets.get("MONDAY_API_TOKEN", "")
            self.board_id = board_id or st.secrets.get("MONDAY_BOARD_ID", "")
        except Exception:
            self.api_token = api_token or ""
            self.board_id = board_id or ""
        
        self.headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        }
    
    def is_configured(self) -> bool:
        """Prüft ob Monday.com korrekt konfiguriert ist"""
        return bool(self.api_token and self.board_id)
    
    def create_item(self, item_name: str, column_values: Dict) -> Optional[str]:
        """
        Erstellt ein neues Item in Monday.com
        
        Args:
            item_name: Name des Items (z.B. Angebots-Nummer)
            column_values: Dictionary mit Spalten-IDs und Werten
            
        Returns:
            Item ID bei Erfolg, None bei Fehler
        """
        if not self.is_configured():
            return None
        
        # Column Values als JSON String formatieren
        column_values_json = json.dumps(column_values).replace('"', '\\"')
        
        query = f"""
        mutation {{
            create_item (
                board_id: {self.board_id},
                item_name: "{item_name}",
                column_values: "{column_values_json}"
            ) {{
                id
            }}
        }}
        """
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'create_item' in data['data']:
                    return data['data']['create_item']['id']
            
            return None
            
        except Exception as e:
            print(f"Monday.com API Error: {e}")
            return None
    
    def save_quote_to_monday(self, quote_data: Dict, pdf_path: str = None) -> bool:
        """
        Speichert ein Angebot in Monday.com
        
        Args:
            quote_data: Dictionary mit Angebotsdaten
            pdf_path: Optionaler Pfad zur PDF-Datei
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not self.is_configured():
            return False
        
        # Column Values vorbereiten
        column_values = {}
        
        # Datum
        if 'datum' in quote_data:
            date_obj = quote_data['datum']
            if isinstance(date_obj, str):
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
            column_values['date_mknqdvj8'] = date_obj.strftime("%Y-%m-%d")
        else:
            column_values['date_mknqdvj8'] = datetime.now().strftime("%Y-%m-%d")
        
        # Angebotswert (Numeric)
        if 'angebotswert' in quote_data:
            column_values['numeric_mknst7mm'] = str(quote_data['angebotswert'])
        
        # Partner (Dropdown)
        if 'partner' in quote_data:
            column_values['dropdown_mknagc5a'] = quote_data['partner']
        
        # PLZ (Text)
        if 'plz' in quote_data:
            column_values['text_mkn9v26m'] = str(quote_data['plz'])
        
        # Item Name (Angebots-Nr oder Kunde)
        item_name = quote_data.get('angebots_nr', quote_data.get('kunde', 'Neues Angebot'))
        
        # Item erstellen
        item_id = self.create_item(item_name, column_values)
        
        if not item_id:
            return False
        
        # Optional: PDF hochladen (wenn Pfad angegeben)
        if pdf_path:
            self.upload_file_to_item(item_id, pdf_path)
        
        return True
    
    def upload_file_to_item(self, item_id: str, file_path: str) -> bool:
        """
        Lädt eine Datei zu einem Monday Item hoch
        
        Args:
            item_id: ID des Monday Items
            file_path: Pfad zur Datei
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        # Implementierung für File Upload (erfordert multipart/form-data)
        # Wird bei Bedarf erweitert
        return False
    
    def get_board_data(self) -> Optional[Dict]:
        """
        Lädt Board-Daten von Monday.com
        
        Returns:
            Board Daten als Dictionary oder None
        """
        if not self.is_configured():
            return None
        
        query = f"""
        query {{
            boards (ids: {self.board_id}) {{
                name
                items {{
                    name
                    column_values {{
                        id
                        text
                        value
                    }}
                }}
            }}
        }}
        """
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            print(f"Monday.com API Error: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Testet die Verbindung zu Monday.com
        
        Returns:
            True wenn verbunden, False sonst
        """
        if not self.is_configured():
            return False
        
        query = """
        query {
            me {
                name
                email
            }
        }
        """
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"query": query},
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception:
            return False


# Helper Funktionen für Streamlit Integration

def init_monday_integration() -> MondayIntegration:
    """Initialisiert Monday Integration in Session State"""
    if 'monday_client' not in st.session_state:
        st.session_state.monday_client = MondayIntegration()
    return st.session_state.monday_client


def save_quote_to_monday_ui(quote_data: Dict, pdf_path: str = None):
    """
    Speichert Angebot in Monday.com mit UI-Feedback
    
    Args:
        quote_data: Angebotsdaten
        pdf_path: Pfad zur PDF (optional)
    """
    monday = init_monday_integration()
    
    if not monday.is_configured():
        st.warning("⚠️ Monday.com nicht konfiguriert. Bitte API Token und Board ID in Secrets hinterlegen.")
        return False
    
    with st.spinner("📤 Speichere in Monday.com..."):
        success = monday.save_quote_to_monday(quote_data, pdf_path)
    
    if success:
        st.success("✅ Angebot erfolgreich in Monday.com gespeichert!")
        return True
    else:
        st.error("❌ Fehler beim Speichern in Monday.com")
        return False


def render_monday_status():
    """Zeigt Monday.com Status in Sidebar an"""
    monday = init_monday_integration()
    
    st.markdown("### 🔗 Monday.com Status")
    
    if monday.is_configured():
        if monday.test_connection():
            st.success("✅ Verbunden")
        else:
            st.error("❌ Verbindungsfehler")
    else:
        st.info("⚙️ Nicht konfiguriert")
        with st.expander("ℹ️ Konfiguration"):
            st.markdown("""
            **Erforderliche Secrets:**
            - `MONDAY_API_TOKEN`
            - `MONDAY_BOARD_ID`
            
            Diese müssen in Streamlit Secrets oder .streamlit/secrets.toml hinterlegt werden.
            """)
