# ==========================================
# MONDAY.COM API TESTER
# Testet alle Funktionen der Monday.com Integration
# ==========================================

import streamlit as st
import requests
import json
from datetime import datetime
from io import BytesIO

def test_monday_api():
    """
    Vollständiger Test der Monday.com API
    """
    st.markdown("## 🔧 Monday.com API Tester")
    st.markdown("---")
    
    # 1. SECRETS LADEN
    st.markdown("### 1️⃣ Konfiguration")
    
    try:
        api_token = st.secrets.get("MONDAY_API_TOKEN", "")
        board_id = st.secrets.get("MONDAY_BOARD_ID", "")
        
        if api_token and board_id:
            st.success("✅ Secrets gefunden")
            st.code(f"""
API Token: {api_token[:30]}... (length: {len(api_token)})
Board ID: {board_id}
            """)
        else:
            st.error("❌ Secrets fehlen!")
            return
            
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        return
    
    st.markdown("---")
    
    # 2. VERBINDUNGSTEST
    st.markdown("### 2️⃣ Verbindungstest")
    
    if st.button("🔌 Verbindung testen"):
        query = """
        query {
            me {
                name
                email
                account {
                    name
                }
            }
        }
        """
        
        headers = {
            "Authorization": api_token,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                "https://api.monday.com/v2",
                headers=headers,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'me' in data['data']:
                    user = data['data']['me']
                    st.success(f"✅ Verbunden als **{user['name']}** ({user['email']})")
                    st.info(f"Account: {user['account']['name']}")
                else:
                    st.error(f"❌ Unerwartete Antwort: {data}")
            else:
                st.error(f"❌ HTTP {response.status_code}")
                st.code(response.text)
                
        except Exception as e:
            st.error(f"❌ Fehler: {e}")
    
    st.markdown("---")
    
    # 3. BOARD PRÜFEN
    st.markdown("### 3️⃣ Board-Informationen")
    
    if st.button("📋 Board laden"):
        query = f"""
        query {{
            boards (ids: {board_id}) {{
                name
                description
                columns {{
                    id
                    title
                    type
                }}
                items_page (limit: 5) {{
                    items {{
                        name
                        created_at
                    }}
                }}
            }}
        }}
        """
        
        headers = {
            "Authorization": api_token,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                "https://api.monday.com/v2",
                headers=headers,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'boards' in data['data']:
                    board = data['data']['boards'][0]
                    
                    st.success(f"✅ Board: **{board['name']}**")
                    
                    # Spalten
                    st.markdown("**Spalten:**")
                    for col in board['columns']:
                        st.write(f"- `{col['id']}` - {col['title']} ({col['type']})")
                    
                    # Items
                    if board['items_page']['items']:
                        st.markdown("**Letzte Items:**")
                        for item in board['items_page']['items']:
                            st.write(f"- {item['name']} ({item['created_at']})")
                else:
                    st.error(f"❌ Board nicht gefunden: {data}")
            else:
                st.error(f"❌ HTTP {response.status_code}")
                st.code(response.text)
                
        except Exception as e:
            st.error(f"❌ Fehler: {e}")
    
    st.markdown("---")
    
    # 4. TEST-ITEM ERSTELLEN
    st.markdown("### 4️⃣ Test-Item erstellen")
    
    with st.form("test_item_form"):
        item_name = st.text_input("Item Name", f"TEST_{datetime.now().strftime('%H%M%S')}")
        test_wert = st.number_input("Test-Wert", 0.0, 100000.0, 1234.56)
        test_partner = st.text_input("Partner", "°coolsulting")
        test_plz = st.text_input("PLZ", "4020")
        
        submit = st.form_submit_button("📤 Item erstellen")
        
        if submit:
            # Column Values
            column_values = {
                "date_mknqdvj8": datetime.now().strftime("%Y-%m-%d"),
                "numeric_mknst7mm": str(test_wert),
                "dropdown_mknagc5a": test_partner,
                "text_mkn9v26m": test_plz,
                "status": "Angebot"
            }
            
            # Escape für GraphQL
            column_values_escaped = json.dumps(column_values).replace('"', '\\"')
            item_name_escaped = item_name.replace('"', '\\"')
            
            query = f'''
            mutation {{
                create_item (
                    board_id: {board_id},
                    item_name: "{item_name_escaped}",
                    column_values: "{column_values_escaped}"
                ) {{
                    id
                    name
                }}
            }}
            '''
            
            headers = {
                "Authorization": api_token,
                "Content-Type": "application/json"
            }
            
            try:
                with st.spinner("Erstelle Item..."):
                    response = requests.post(
                        "https://api.monday.com/v2",
                        headers=headers,
                        json={"query": query},
                        timeout=10
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'create_item' in data['data']:
                        item = data['data']['create_item']
                        st.success(f"✅ Item erstellt: **{item['name']}** (ID: {item['id']})")
                        st.session_state['last_item_id'] = item['id']
                    else:
                        st.error(f"❌ Fehler: {data}")
                        st.code(json.dumps(data, indent=2))
                else:
                    st.error(f"❌ HTTP {response.status_code}")
                    st.code(response.text)
                    
            except Exception as e:
                st.error(f"❌ Fehler: {e}")
    
    st.markdown("---")
    
    # 5. PDF UPLOAD TESTEN
    st.markdown("### 5️⃣ PDF Upload testen")
    
    if 'last_item_id' in st.session_state:
        st.info(f"Nutze letztes Item: {st.session_state['last_item_id']}")
        
        if st.button("📎 Test-PDF hochladen"):
            # Einfaches Test-PDF erstellen
            try:
                from fpdf import FPDF
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="TEST PDF", ln=True, align='C')
                pdf.cell(200, 10, txt=f"Created: {datetime.now()}", ln=True, align='C')
                
                # PDF als Bytes
                pdf_bytes = bytes(pdf.output())
                
                # Upload zu Monday
                item_id = st.session_state['last_item_id']
                filename = f"TEST_{datetime.now().strftime('%H%M%S')}.pdf"
                column_id = "file_mkngj4yq"
                
                # GraphQL Mutation
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
                
                map_data = {
                    "image": ["variables.file"]
                }
                
                # Multipart Form
                files = {
                    'query': (None, query),
                    'variables': (None, json.dumps(variables)),
                    'map': (None, json.dumps(map_data)),
                    'image': (filename, pdf_bytes, 'application/pdf')
                }
                
                upload_headers = {
                    "Authorization": api_token
                }
                
                with st.spinner("Lade PDF hoch..."):
                    response = requests.post(
                        "https://api.monday.com/v2/file",
                        headers=upload_headers,
                        files=files,
                        timeout=30
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'add_file_to_column' in data['data']:
                        st.success("✅ PDF erfolgreich hochgeladen!")
                        st.code(json.dumps(data, indent=2))
                    else:
                        st.error(f"❌ Upload-Fehler: {data}")
                else:
                    st.error(f"❌ HTTP {response.status_code}")
                    st.code(response.text)
                    
            except Exception as e:
                st.error(f"❌ Fehler: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.warning("⚠️ Erstelle zuerst ein Test-Item (siehe oben)")
    
    st.markdown("---")
    
    # 6. SPALTEN-IDS PRÜFEN
    st.markdown("### 6️⃣ Spalten-IDs Referenz")
    
    st.code("""
# Deine konfigurierten Spalten-IDs:

date_mknqdvj8       → Datum (Date)
file_mkngj4yq       → Datei (File)
numeric_mknst7mm    → Angebotswert (Number)
dropdown_mknagc5a   → Partner (Dropdown)
text_mkn9v26m       → PLZ (Text)

# Stelle sicher, dass diese IDs mit deinem Board übereinstimmen!
# Prüfen mit: Board Info laden (oben)
    """)


if __name__ == "__main__":
    st.set_page_config(page_title="Monday.com Tester", layout="wide")
    test_monday_api()