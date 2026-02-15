# ==========================================
# DATEI: coolmatch_database.py
# VERSION: 7.1 - Turso Cloud Support
# AUTOR: Michael Schäpers, coolsulting
# ==========================================

import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import streamlit as st


def _get_connection():
    """Turso wenn Secrets vorhanden, sonst lokale SQLite"""
    try:
        turso_url = st.secrets.get("TURSO_URL", "")
        turso_token = st.secrets.get("TURSO_TOKEN", "")
    except Exception:
        turso_url = ""
        turso_token = ""

    if turso_url and turso_token:
        import libsql_experimental as libsql
        conn = libsql.connect(database=turso_url, auth_token=turso_token)
        return conn, "turso"
    else:
        import sqlite3, os, tempfile
        data_dir = os.path.join(tempfile.gettempdir(), "coolmatch_data")
        os.makedirs(data_dir, exist_ok=True)
        conn = sqlite3.connect(os.path.join(data_dir, "coolmatch_database.db"))
        return conn, "sqlite"


def _fetchall(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall(), cur.description


def _execute(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


class CoolMatchDatabase:
    """Verwaltet alle Angebots-Daten in SQLite / Turso"""

    def __init__(self, db_path: str = None):
        self.init_database()

    def init_database(self):
        conn, mode = _get_connection()
        sqls = [
            """CREATE TABLE IF NOT EXISTS angebote (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                angebots_nr TEXT UNIQUE NOT NULL,
                kunde_name TEXT NOT NULL,
                kunde_projekt TEXT,
                kunde_nr TEXT,
                erstellt_am DATETIME DEFAULT CURRENT_TIMESTAMP,
                gueltig_bis DATE,
                bearbeiter TEXT,
                firma TEXT,
                summe_netto REAL,
                summe_brutto REAL,
                mwst_satz REAL,
                rabatt_prozent REAL,
                rabatt_absolut REAL,
                manual_preis BOOLEAN DEFAULT 0,
                preise_verborgen BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'Erstellt',
                monday_item_id TEXT,
                closing_text TEXT,
                notizen TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS positionen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                angebots_id INTEGER NOT NULL,
                position_nr INTEGER NOT NULL,
                typ TEXT, artikel_nr TEXT, beschreibung TEXT,
                menge REAL, einzelpreis REAL, rabatt REAL, gesamt REAL, notiz TEXT,
                FOREIGN KEY (angebots_id) REFERENCES angebote(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS produkt_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artikel_nr TEXT NOT NULL, beschreibung TEXT, kategorie TEXT,
                preis REAL, rabatt REAL, menge REAL,
                datum DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_angebots_nr ON angebote(angebots_nr)",
            "CREATE INDEX IF NOT EXISTS idx_kunde ON angebote(kunde_name)",
            "CREATE INDEX IF NOT EXISTS idx_datum ON angebote(erstellt_am)",
            "CREATE INDEX IF NOT EXISTS idx_status ON angebote(status)",
            "CREATE INDEX IF NOT EXISTS idx_artikel ON produkt_stats(artikel_nr)",
        ]
        for sql in sqls:
            try:
                _execute(conn, sql)
            except Exception:
                pass
        conn.commit()
        conn.close()

    def _query_to_df(self, sql, params=()):
        conn, mode = _get_connection()
        rows, desc = _fetchall(conn, sql, params)
        conn.close()
        if desc:
            return pd.DataFrame(rows, columns=[d[0] for d in desc])
        return pd.DataFrame()

    def save_quote(self, quote_header: Dict, positions: List[Dict]) -> int:
        conn, mode = _get_connection()
        try:
            _execute(conn, """
                INSERT INTO angebote
                (angebots_nr, kunde_name, kunde_projekt, kunde_nr, gueltig_bis,
                 bearbeiter, firma, summe_netto, summe_brutto, mwst_satz,
                 rabatt_prozent, rabatt_absolut, manual_preis, preise_verborgen,
                 status, monday_item_id, closing_text, notizen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quote_header['angebots_nr'], quote_header['kunde_name'],
                quote_header.get('kunde_projekt', ''), quote_header.get('kunde_nr', ''),
                quote_header.get('gueltig_bis', ''), quote_header.get('bearbeiter', ''),
                quote_header.get('firma', ''), quote_header['summe_netto'],
                quote_header['summe_brutto'], quote_header['mwst_satz'],
                quote_header.get('rabatt_prozent', 0), quote_header.get('rabatt_absolut', 0),
                quote_header.get('manual_preis', 0), quote_header.get('preise_verborgen', 0),
                quote_header.get('status', 'Erstellt'), quote_header.get('monday_item_id', ''),
                quote_header.get('closing_text', ''), quote_header.get('notizen', '')
            ))
            rows, _ = _fetchall(conn, "SELECT last_insert_rowid()")
            angebots_id = rows[0][0]
            for pos in positions:
                _execute(conn, """
                    INSERT INTO positionen
                    (angebots_id, position_nr, typ, artikel_nr, beschreibung,
                     menge, einzelpreis, rabatt, gesamt, notiz)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    angebots_id, pos.get('Pos', 0), pos.get('Typ', ''),
                    pos.get('Artikel', ''), pos.get('Beschreibung', ''),
                    pos.get('Menge', 0), pos.get('Einzelpreis', 0), pos.get('Rabatt', 0),
                    pos.get('Menge', 0) * pos.get('Einzelpreis', 0) * (1 - pos.get('Rabatt', 0)/100),
                    pos.get('Notiz', '')
                ))
                _execute(conn, """
                    INSERT INTO produkt_stats (artikel_nr, beschreibung, kategorie, preis, rabatt, menge)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    pos.get('Artikel', ''), pos.get('Beschreibung', ''), pos.get('Typ', ''),
                    pos.get('Einzelpreis', 0), pos.get('Rabatt', 0), pos.get('Menge', 0)
                ))
            conn.commit()
            return angebots_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_all_quotes(self, limit: int = None) -> pd.DataFrame:
        sql = "SELECT * FROM angebote ORDER BY erstellt_am DESC"
        if limit:
            sql += f" LIMIT {limit}"
        return self._query_to_df(sql)

    def get_quote_by_nr(self, angebots_nr: str) -> Optional[Dict]:
        conn, mode = _get_connection()
        rows, _ = _fetchall(conn, "SELECT * FROM angebote WHERE angebots_nr = ?", (angebots_nr,))
        if not rows:
            conn.close()
            return None
        header = rows[0]
        pos_rows, _ = _fetchall(conn,
            "SELECT * FROM positionen WHERE angebots_id = ? ORDER BY position_nr", (header[0],))
        conn.close()
        return {'header': header, 'positions': pos_rows}

    def get_statistics(self) -> Dict:
        conn, mode = _get_connection()
        rows, _ = _fetchall(conn, """
            SELECT COUNT(*), SUM(summe_brutto), AVG(summe_brutto),
                   MIN(summe_brutto), MAX(summe_brutto) FROM angebote
        """)
        row = rows[0]
        conn.close()
        stats = {'gesamt': {
            'anzahl': row[0] or 0, 'summe': row[1] or 0,
            'durchschnitt': row[2] or 0, 'min': row[3] or 0, 'max': row[4] or 0
        }}
        stats['monthly'] = self._query_to_df("""
            SELECT strftime('%Y-%m', erstellt_am) as monat,
                   COUNT(*) as anzahl, SUM(summe_brutto) as summe
            FROM angebote GROUP BY monat ORDER BY monat DESC LIMIT 12
        """)
        stats['top_products'] = self._query_to_df("""
            SELECT artikel_nr, beschreibung, kategorie, COUNT(*) as anzahl,
                   SUM(menge) as gesamt_menge, AVG(preis) as durchschnittspreis,
                   AVG(rabatt) as durchschnittsrabatt
            FROM produkt_stats GROUP BY artikel_nr ORDER BY anzahl DESC LIMIT 15
        """)
        stats['categories'] = self._query_to_df("""
            SELECT kategorie, COUNT(*) as anzahl,
                   SUM(menge * preis * (1 - rabatt/100)) as umsatz
            FROM produkt_stats WHERE kategorie != ''
            GROUP BY kategorie ORDER BY umsatz DESC
        """)
        stats['status'] = self._query_to_df("""
            SELECT status, COUNT(*) as anzahl, SUM(summe_brutto) as summe
            FROM angebote GROUP BY status
        """)
        return stats

    def search_quotes(self, search_term: str) -> pd.DataFrame:
        p = f"%{search_term}%"
        return self._query_to_df("""
            SELECT * FROM angebote
            WHERE kunde_name LIKE ? OR angebots_nr LIKE ?
            OR kunde_projekt LIKE ? OR kunde_nr LIKE ?
            ORDER BY erstellt_am DESC
        """, (p, p, p, p))

    def update_monday_id(self, angebots_nr: str, monday_item_id: str):
        conn, mode = _get_connection()
        _execute(conn, "UPDATE angebote SET monday_item_id = ? WHERE angebots_nr = ?",
                 (monday_item_id, angebots_nr))
        conn.commit()
        conn.close()

    def update_status(self, angebots_nr: str, status: str):
        conn, mode = _get_connection()
        _execute(conn, "UPDATE angebote SET status = ? WHERE angebots_nr = ?",
                 (status, angebots_nr))
        conn.commit()
        conn.close()

    def delete_quote(self, angebots_nr: str):
        conn, mode = _get_connection()
        rows, _ = _fetchall(conn, "SELECT id FROM angebote WHERE angebots_nr = ?", (angebots_nr,))
        if rows:
            aid = rows[0][0]
            _execute(conn, "DELETE FROM positionen WHERE angebots_id = ?", (aid,))
            _execute(conn, "DELETE FROM angebote WHERE id = ?", (aid,))
            conn.commit()
        conn.close()

    def export_to_excel(self, filepath: str):
        conn, mode = _get_connection()
        rows_a, desc_a = _fetchall(conn, "SELECT * FROM angebote")
        rows_p, desc_p = _fetchall(conn, "SELECT * FROM positionen")
        conn.close()
        df_a = pd.DataFrame(rows_a, columns=[d[0] for d in desc_a]) if desc_a else pd.DataFrame()
        df_p = pd.DataFrame(rows_p, columns=[d[0] for d in desc_p]) if desc_p else pd.DataFrame()
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_a.to_excel(writer, sheet_name='Angebote', index=False)
            df_p.to_excel(writer, sheet_name='Positionen', index=False)
            pd.DataFrame([self.get_statistics()['gesamt']]).to_excel(
                writer, sheet_name='Statistiken', index=False)