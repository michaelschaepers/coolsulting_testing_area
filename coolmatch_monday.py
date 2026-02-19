# ==========================================
# DATEI: coolmatch_monday.py
# VERSION: 7.2 - FIXED COLUMN IDs + DROPDOWN FORMAT
# AUTOR: Michael Schäpers, coolsulting
# FIXES:
#   - 'status' → korrekte Column-ID 'color_mkncgyk5'
#   - Dropdown-Format: {"labels": ["Wert"]} statt plain String
#   - Status-Column-Format: {"label": "Angebot"} statt plain String
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
    """
    try:
        api_token = st.secrets.get("MONDAY_API_TOKEN", "")
        board_id = st.secrets.get("MONDAY_BOARD_ID", "")

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
        self.api_url = "https://api.monday.com/v2"
        self.file_api_url = "https://api.monday.com/v2/file"

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
        return bool(self.api_token and self.board_id)

    def create_item(self, item_name: str, column_values: Dict) -> Optional[str]:
        """
        Erstellt ein neues Item in Monday.com.
        Bei ColumnValueException (z.B. unbekannter Dropdown-Wert) →
        automatischer Retry ohne die problematische Spalte.
        """
        if not self.is_configured():
            return None

        def _try_create(cv: Dict) -> Optional[str]:
            cv_json = json.dumps(cv)
            cv_escaped = cv_json.replace("\\", "\\\\").replace('"', '\\"')
            item_name_escaped = item_name.replace("\\", "\\\\").replace('"', '\\"')
            query = f'''
            mutation {{
                create_item (
                    board_id: {self.board_id},
                    item_name: "{item_name_escaped}",
                    column_values: "{cv_escaped}"
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
                    # Prüfe auf ColumnValueException
                    if 'errors' in data:
                        for err in data['errors']:
                            code = err.get('extensions', {}).get('code', '')
                            if code == 'ColumnValueException':
                                return 'COLUMN_ERROR'
                        print(f"Monday.com GraphQL Error: {data['errors']}")
                        return None
                    if 'data' in data and data['data'] and 'create_item' in data['data']:
                        item = data['data']['create_item']
                        if item:
                            return item['id']
                else:
                    print(f"Monday.com HTTP Error: {response.status_code}")
                return None
            except Exception as e:
                print(f"Monday.com API Error: {e}")
                return None

        # Versuch 1: Mit allen Feldern
        result = _try_create(column_values)

        # Versuch 2: Bei Dropdown-Fehler → ohne Dropdown-Spalten wiederholen
        if result == 'COLUMN_ERROR':
            print("⚠️ ColumnValueException → Retry ohne Dropdown-Spalten")
            cv_fallback = {k: v for k, v in column_values.items()
                          if not k.startswith('dropdown_') and not k.startswith('color_')}
            result = _try_create(cv_fallback)

        return result if result and result != 'COLUMN_ERROR' else None

    def upload_file_to_item(self, item_id: str, file_bytes: bytes, filename: str,
                            column_id: str = "file_mkngj4yq") -> bool:
        """
        Lädt eine Datei zu einem Monday Item hoch
        """
        if not self.is_configured():
            return False

        try:
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

            variables = {
                "itemId": int(item_id),
                "columnId": column_id
            }

            map_data = {"image": ["variables.file"]}

            files = {
                'query': (None, query),
                'variables': (None, json.dumps(variables)),
                'map': (None, json.dumps(map_data)),
                'image': (filename, file_bytes, 'application/pdf')
            }

            upload_headers = {"Authorization": self.api_token}

            response = requests.post(
                self.file_api_url,
                headers=upload_headers,
                files=files,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and 'add_file_to_column' in data['data']:
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
                             filename: str = None) -> tuple:
        """
        Speichert ein Angebot in Monday.com mit PDF.

        FIX: Korrekte Column-Formate für alle Spaltentypen:
          - date   → {"date": "YYYY-MM-DD"}
          - number → plain String "123.45"
          - dropdown → {"labels": ["Wert"]}   (⚠ war bisher falscher Plain-String)
          - status → {"label": "Wert"}         (⚠ war bisher 'status' als Column-ID)
          - text   → plain String
        """
        if not self.is_configured():
            return False, ""

        column_values = {}

        # ── Datum (date) ──
        if 'datum' in quote_data:
            date_obj = quote_data['datum']
            if isinstance(date_obj, str):
                try:
                    date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
                except Exception:
                    date_obj = datetime.now()
            column_values['date_mknqdvj8'] = {"date": date_obj.strftime("%Y-%m-%d")}
        else:
            column_values['date_mknqdvj8'] = {"date": datetime.now().strftime("%Y-%m-%d")}

        # ── Angebotswert (numeric) ── plain String
        if 'angebotswert' in quote_data:
            column_values['numeric_mknst7mm'] = str(round(float(quote_data['angebotswert']), 2))

        # ── Partner (dropdown) ── nur setzen wenn Label bekannt, sonst weglassen
        # Verhindert ColumnValueException wenn Label nicht in Monday existiert
        if 'partner' in quote_data:
            partner_raw = str(quote_data['partner']).lstrip('°').strip()
            if partner_raw:
                partner_clean = partner_raw[0].upper() + partner_raw[1:]
                column_values['dropdown_mknagc5a'] = {"labels": [partner_clean]}

        # ── PLZ (text) ── plain String
        if 'plz' in quote_data:
            column_values['text_mkn9v26m'] = str(quote_data['plz'])

        # ── Status (status-Spalte) ── korrekte Column-ID aus Board: color_mkncgyk5
        # FIX: früher stand hier 'status' als Column-ID → existiert nicht → Fehler
        column_values['color_mkncgyk5'] = {"label": "Angebot"}

        # Item-Name
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
        if not self.is_configured():
            return None

        query = f"""
        query {{
            boards (ids: {self.board_id}) {{
                name
                items_page {{
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

    def test_connection(self) -> tuple:
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
                if 'data' in data and data['data'] and 'me' in data['data']:
                    user = data['data']['me']
                    return True, f"Verbunden als {user['name']} ({user['email']})"
                elif 'errors' in data:
                    return False, f"GraphQL Error: {data['errors']}"

            return False, f"HTTP {response.status_code}: {response.text[:100]}"

        except Exception as e:
            return False, f"Exception: {str(e)}"


# ── Streamlit Helper ──

def init_monday_integration() -> MondayIntegration:
    if 'monday_client' not in st.session_state:
        st.session_state.monday_client = MondayIntegration()
    return st.session_state.monday_client


def save_quote_to_monday_ui(quote_data: Dict, pdf_bytes: bytes = None,
                             filename: str = None) -> bool:
    monday = init_monday_integration()

    if not monday.is_configured():
        st.warning("⚠️ Monday.com nicht konfiguriert.")
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
Token: {'✔' if monday.api_token else '✗'}
Board ID: {'✔' if monday.board_id else '✗'}
API URL: {monday.api_url}
                """)
    else:
        st.info("⚙️ Nicht konfiguriert")
        with st.expander("ℹ️ Konfiguration"):
            st.markdown("""
            **Erforderliche Secrets:**
            ```toml
            # .streamlit/secrets.toml
            MONDAY_API_TOKEN = "eyJhbG..."
            MONDAY_BOARD_ID  = "1234567890"
            ```

            **Korrekte Column IDs (aus Board):**
            | Feld          | Column-ID           | Typ      |
            |---------------|---------------------|----------|
            | Datum         | date_mknqdvj8       | date     |
            | Datei         | file_mkngj4yq       | file     |
            | Angebotswert  | numeric_mknst7mm    | number   |
            | Partner       | dropdown_mknagc5a   | dropdown |
            | PLZ           | text_mkn9v26m       | text     |
            | Status        | color_mkncgyk5      | status   |
            """)
