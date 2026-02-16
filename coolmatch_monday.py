# ==========================================
# DATEI: coolmatch_monday.py
# VERSION: 7.1 - FIXED + KOMPATIBEL
# AUTOR: Michael Schäpers, coolsulting
# ÄNDERUNGEN: PDF-Upload implementiert + Kompatibel mit alten Secret-Namen
# ==========================================

import requests
import json
from datetime import datetime
from typing import Dict, Optional, Union
import streamlit as st
import io


def get_monday_secrets():
    """
    Lädt Monday Secrets mit Fallback auf alte Namen
    Unterstützt sowohl:
    - MONDAY_API_TOKEN / MONDAY_BOARD_ID (neu)
    - monday_key / monday_board_id (alt)
    """
    try:
        # Versuche neue Namen
        api_token = st.secrets.get("MONDAY_API_TOKEN", "")
        board_id = st.secrets.get("MONDAY_BOARD_ID", "")
        
        # Fallback auf alte Namen
        if not api_token:
            api_token = st.secrets.get("monday_key", "")
        
        if not board_id:
            board_id = st.secrets.get("monday_board_id", "")
        
        return api_token, board_id
    
    except Exception:
        return "", ""


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
        self.file_api_url = "https://api.monday.com/v2/file"
        
        # Token und Board ID mit Fallback auf alte Namen laden
        if api_token is None or board_id is None:
            default_token, default_board = get_monday_secrets()
            self.api_token = api_token or default_token
            self.board_id = board_id or default_board
        else:
            self.api_token = api_token
            self.board_id = board_id
        
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
        
        # Escape special characters in values
        def escape_json(obj):
            """Escape für JSON-String in GraphQL"""
            return json.dumps(obj).replace('"', '\\"')
        
        column_values_escaped = escape_json(column_values)
        item_name_escaped = item_name.replace('"', '\\"')
        
        query = f'''
        mutation {{
            create_item (
                board_id: {self.board_id},
                item_name: "{item_name_escaped}",
                column_values: "{column_values_escaped}"
            ) {{
                id
            }}
        }}
        '''
        
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
                elif 'errors' in data:
                    print(f"Monday.com GraphQL Error: {data['errors']}")
            else:
                print(f"Monday.com HTTP Error: {response.status_code} - {response.text}")
            
            return None
            
        except Exception as e:
            print(f"Monday.com API Error: {e}")
            return None
    
    def upload_file_to_item(self, item_id: str, file_bytes: bytes, filename: str, 
                           column_id: str = "file_mkngj4yq") -> bool:
        """
        Lädt eine Datei zu einem Monday Item hoch (FIXED VERSION)
        
        Args:
            item_id: ID des Monday Items
            file_bytes: PDF als Bytes
            filename: Dateiname (z.B. "AN_2026001.pdf")
            column_id: Spalten-ID für File Column
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not self.is_configured():
            return False
        
        try:
            # GraphQL Mutation für File Upload
            query = '''
            mutation ($file: File!, $itemId: ID!, $columnId: String!) {
                add_file_to_column (
                    file: $file,
                    item_id: $itemId,
                    column_id: $columnId
                ) {
                    id
                    name
                }
            }
            '''
            
            # Variables für GraphQL
            variables = {
                "itemId": int(item_id),
                "columnId": column_id
            }
            
            # Map für File Upload
            map_data = {
                "image": ["variables.file"]
            }
            
            # Multipart Form Data
            files = {
                'query': (None, query),
                'variables': (None, json.dumps(variables)),
                'map': (None, json.dumps(map_data)),
                'image': (filename, file_bytes, 'application/pdf')
            }
            
            # Authorization Header ohne Content-Type (wird von requests gesetzt)
            upload_headers = {
                "Authorization": self.api_token
            }
            
            response = requests.post(
                self.file_api_url,
                headers=upload_headers,
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'add_file_to_column' in data['data']:
                    return True
                elif 'errors' in data:
                    print(f"Monday.com File Upload Error: {data['errors']}")
            else:
                print(f"Monday.com File Upload HTTP Error: {response.status_code} - {response.text}")
            
            return False
            
        except Exception as e:
            print(f"Monday.com File Upload Exception: {e}")
            return False
    
    def save_quote_to_monday(self, quote_data: Dict, pdf_bytes: bytes = None, 
                            filename: str = None) -> tuple[bool, str]:
        """
        Speichert ein Angebot in Monday.com mit PDF
        
        Args:
            quote_data: Dictionary mit Angebotsdaten
            pdf_bytes: PDF als Bytes (nicht Dateipfad!)
            filename: Dateiname für PDF
            
        Returns:
            (success: bool, monday_item_id: str)
        """
        if not self.is_configured():
            return False, ""
        
        # Column Values vorbereiten
        column_values = {}
        
        # Datum
        if 'datum' in quote_data:
            date_obj = quote_data['datum']
            if isinstance(date_obj, str):
                try:
                    date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
                except:
                    date_obj = datetime.now()
            column_values['date_mknqdvj8'] = date_obj.strftime("%Y-%m-%d")
        else:
            column_values['date_mknqdvj8'] = datetime.now().strftime("%Y-%m-%d")
        
        # Angebotswert (Numeric) - WICHTIG: Als STRING
        if 'angebotswert' in quote_data:
            column_values['numeric_mknst7mm'] = str(round(float(quote_data['angebotswert']), 2))
        
        # Partner (Dropdown) - WICHTIG: Als STRING
        if 'partner' in quote_data:
            column_values['dropdown_mknagc5a'] = str(quote_data['partner'])
        
        # PLZ (Text)
        if 'plz' in quote_data:
            column_values['text_mkn9v26m'] = str(quote_data['plz'])
        
        # Status setzen
        column_values['status'] = "Angebot"
        
        # Item Name (Angebots-Nr oder Kunde)
        item_name = quote_data.get('angebots_nr', quote_data.get('kunde', 'Neues Angebot'))
        
        # Item erstellen
        item_id = self.create_item(item_name, column_values)
        
        if not item_id:
            return False, ""
        
        # PDF hochladen (wenn vorhanden)
        if pdf_bytes and filename:
            pdf_success = self.upload_file_to_item(item_id, pdf_bytes, filename)
            if not pdf_success:
                print(f"⚠️ Warning: Item created ({item_id}) but PDF upload failed")
        
        return True, item_id
    
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
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Testet die Verbindung zu Monday.com
        
        Returns:
            (connected: bool, message: str)
        """
        if not self.is_configured():
            return False, "API Token oder Board ID fehlt"
        
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
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'me' in data['data']:
                    user = data['data']['me']
                    return True, f"Verbunden als {user['name']} ({user['email']})"
                elif 'errors' in data:
                    return False, f"GraphQL Error: {data['errors']}"
            
            return False, f"HTTP {response.status_code}: {response.text[:100]}"
            
        except Exception as e:
            return False, f"Exception: {str(e)}"


# Helper Funktionen für Streamlit Integration

def init_monday_integration() -> MondayIntegration:
    """Initialisiert Monday Integration in Session State"""
    if 'monday_client' not in st.session_state:
        st.session_state.monday_client = MondayIntegration()
    return st.session_state.monday_client


def save_quote_to_monday_ui(quote_data: Dict, pdf_bytes: bytes = None, filename: str = None) -> bool:
    """
    Speichert Angebot in Monday.com mit UI-Feedback
    
    Args:
        quote_data: Angebotsdaten
        pdf_bytes: PDF als Bytes
        filename: Dateiname
    
    Returns:
        True bei Erfolg, False bei Fehler
    """
    monday = init_monday_integration()
    
    if not monday.is_configured():
        st.warning("⚠️ Monday.com nicht konfiguriert. Bitte API Token und Board ID in Secrets hinterlegen.")
        return False
    
    with st.spinner("📤 Speichere in Monday.com..."):
        success, item_id = monday.save_quote_to_monday(quote_data, pdf_bytes, filename)
    
    if success:
        st.success(f"✅ Angebot in Monday.com gespeichert! (Item ID: {item_id})")
        return True
    else:
        st.error("❌ Fehler beim Speichern in Monday.com")
        return False


def render_monday_status():
    """Zeigt Monday.com Status in Sidebar an"""
    monday = init_monday_integration()
    
    st.markdown("### 🔗 Monday.com Status")
    
    if monday.is_configured():
        connected, message = monday.test_connection()
        if connected:
            st.success(f"✅ {message}")
        else:
            st.error(f"❌ {message}")
            with st.expander("🔧 Troubleshooting"):
                st.code(f"""
Token: {'✓' if monday.api_token else '✗'}
Board ID: {'✓' if monday.board_id else '✗'}
API URL: {monday.api_url}
                """)
    else:
        st.info("⚙️ Nicht konfiguriert")
        with st.expander("ℹ️ Konfiguration"):
            st.markdown("""
            **Erforderliche Secrets:**
            ```toml
            # .streamlit/secrets.toml
            # Neue Namen (empfohlen):
            MONDAY_API_TOKEN = "eyJhbG..."
            MONDAY_BOARD_ID = "1234567890"
            
            # ODER alte Namen (auch unterstützt):
            monday_key = "eyJhbG..."
            monday_board_id = "1234567890"
            ```
            
            **Column IDs prüfen:**
            - date_mknqdvj8 → Datum
            - file_mkngj4yq → Datei
            - numeric_mknst7mm → Wert
            - dropdown_mknagc5a → Partner
            - text_mkn9v26m → PLZ
            """)