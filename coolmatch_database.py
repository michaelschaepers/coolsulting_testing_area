# ==========================================
# DATEI: coolmatch_database.py
# VERSION: 7.1 - TURSO CLOUD SUPPORT
# AUTOR: Michael Schäpers, coolsulting
# BESCHREIBUNG: SQLite Datenbank für coolMATCH Angebote
#               Unterstützt Turso Cloud Database
# ==========================================

import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import json
import os

class CoolMatchDatabase:
    """Verwaltet alle Angebots-Daten in SQLite (lokal oder Turso Cloud)"""
    
    def __init__(self, db_path: str = "coolmatch_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Gibt SQLite Connection zurück"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        return sqlite3.connect(self.db_path)
            return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Erstellt Datenbank-Schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabelle: Angebote
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS angebote (
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
            )
        """)
        
        # Tabelle: Positionen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positionen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                angebots_id INTEGER NOT NULL,
                position_nr INTEGER NOT NULL,
                typ TEXT,
                artikel_nr TEXT,
                beschreibung TEXT,
                menge REAL,
                einzelpreis REAL,
                rabatt REAL,
                gesamt REAL,
                notiz TEXT,
                FOREIGN KEY (angebots_id) REFERENCES angebote(id) ON DELETE CASCADE
            )
        """)
        
        # Tabelle: Produkt-Stats (für Analytics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produkt_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artikel_nr TEXT NOT NULL,
                beschreibung TEXT,
                kategorie TEXT,
                preis REAL,
                rabatt REAL,
                menge REAL,
                datum DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indizes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_angebots_nr ON angebote(angebots_nr)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kunde ON angebote(kunde_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_datum ON angebote(erstellt_am)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON angebote(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_artikel ON produkt_stats(artikel_nr)")
        
        conn.commit()
        conn.close()
    
    def save_quote(self, quote_header: Dict, positions: List[Dict]) -> int:
        """
        Speichert komplettes Angebot
        
        Args:
            quote_header: Kopfdaten des Angebots
            positions: Liste mit Positionen
            
        Returns:
            Angebots-ID in Datenbank
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Header speichern
            cursor.execute("""
                INSERT INTO angebote 
                (angebots_nr, kunde_name, kunde_projekt, kunde_nr, gueltig_bis, 
                 bearbeiter, firma, summe_netto, summe_brutto, mwst_satz,
                 rabatt_prozent, rabatt_absolut, manual_preis, preise_verborgen,
                 status, monday_item_id, closing_text, notizen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quote_header['angebots_nr'],
                quote_header['kunde_name'],
                quote_header.get('kunde_projekt', ''),
                quote_header.get('kunde_nr', ''),
                quote_header.get('gueltig_bis', ''),
                quote_header.get('bearbeiter', ''),
                quote_header.get('firma', ''),
                quote_header['summe_netto'],
                quote_header['summe_brutto'],
                quote_header['mwst_satz'],
                quote_header.get('rabatt_prozent', 0),
                quote_header.get('rabatt_absolut', 0),
                quote_header.get('manual_preis', 0),
                quote_header.get('preise_verborgen', 0),
                quote_header.get('status', 'Erstellt'),
                quote_header.get('monday_item_id', ''),
                quote_header.get('closing_text', ''),
                quote_header.get('notizen', '')
            ))
            
            angebots_id = cursor.lastrowid
            
            # Positionen speichern
            for pos in positions:
                cursor.execute("""
                    INSERT INTO positionen
                    (angebots_id, position_nr, typ, artikel_nr, beschreibung,
                     menge, einzelpreis, rabatt, gesamt, notiz)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    angebots_id,
                    pos.get('Pos', 0),
                    pos.get('Typ', ''),
                    pos.get('Artikel', ''),
                    pos.get('Beschreibung', ''),
                    pos.get('Menge', 0),
                    pos.get('Einzelpreis', 0),
                    pos.get('Rabatt', 0),
                    pos.get('Menge', 0) * pos.get('Einzelpreis', 0) * (1 - pos.get('Rabatt', 0)/100),
                    pos.get('Notiz', '')
                ))
                
                # Produkt-Stats aktualisieren
                cursor.execute("""
                    INSERT INTO produkt_stats (artikel_nr, beschreibung, kategorie, preis, rabatt, menge)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    pos.get('Artikel', ''),
                    pos.get('Beschreibung', ''),
                    pos.get('Typ', ''),
                    pos.get('Einzelpreis', 0),
                    pos.get('Rabatt', 0),
                    pos.get('Menge', 0)
                ))
            
            conn.commit()
            return angebots_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_all_quotes(self, limit: int = None) -> pd.DataFrame:
        """Lädt alle Angebote"""
        conn = self.get_connection()
        query = "SELECT * FROM angebote ORDER BY erstellt_am DESC"
        if limit:
            query += f" LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_quote_by_nr(self, angebots_nr: str) -> Optional[Dict]:
        """Lädt spezifisches Angebot mit Positionen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM angebote WHERE angebots_nr = ?", (angebots_nr,))
        header = cursor.fetchone()
        
        if not header:
            conn.close()
            return None
        
        cursor.execute("""
            SELECT * FROM positionen 
            WHERE angebots_id = ? 
            ORDER BY position_nr
        """, (header[0],))
        
        positions = cursor.fetchall()
        conn.close()
        
        return {'header': header, 'positions': positions}
    
    def get_statistics(self) -> Dict:
        """Berechnet Statistiken"""
        conn = self.get_connection()
        stats = {}
        
        # Gesamt-Statistiken
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as anzahl,
                SUM(summe_brutto) as gesamt_brutto,
                AVG(summe_brutto) as durchschnitt_brutto,
                MIN(summe_brutto) as min_brutto,
                MAX(summe_brutto) as max_brutto
            FROM angebote
        """)
        
        row = cursor.fetchone()
        stats['gesamt'] = {
            'anzahl': row[0],
            'summe': row[1] or 0,
            'durchschnitt': row[2] or 0,
            'min': row[3] or 0,
            'max': row[4] or 0
        }
        
        # Monatliche Auswertung
        stats['monthly'] = pd.read_sql_query("""
            SELECT 
                strftime('%Y-%m', erstellt_am) as monat,
                COUNT(*) as anzahl,
                SUM(summe_brutto) as summe
            FROM angebote
            GROUP BY monat
            ORDER BY monat DESC
            LIMIT 12
        """, conn)
        
        # Top Produkte
        stats['top_products'] = pd.read_sql_query("""
            SELECT 
                artikel_nr,
                beschreibung,
                kategorie,
                COUNT(*) as anzahl,
                SUM(menge) as gesamt_menge,
                AVG(preis) as durchschnittspreis,
                AVG(rabatt) as durchschnittsrabatt
            FROM produkt_stats
            GROUP BY artikel_nr
            ORDER BY anzahl DESC
            LIMIT 15
        """, conn)
        
        # Kategorie-Verteilung
        stats['categories'] = pd.read_sql_query("""
            SELECT 
                kategorie,
                COUNT(*) as anzahl,
                SUM(menge * preis * (1 - rabatt/100)) as umsatz
            FROM produkt_stats
            WHERE kategorie != ''
            GROUP BY kategorie
            ORDER BY umsatz DESC
        """, conn)
        
        # Status-Verteilung
        stats['status'] = pd.read_sql_query("""
            SELECT 
                status,
                COUNT(*) as anzahl,
                SUM(summe_brutto) as summe
            FROM angebote
            GROUP BY status
        """, conn)
        
        conn.close()
        return stats
    
    def search_quotes(self, search_term: str) -> pd.DataFrame:
        """Sucht Angebote"""
        conn = self.get_connection()
        query = """
            SELECT * FROM angebote 
            WHERE kunde_name LIKE ? 
            OR angebots_nr LIKE ? 
            OR kunde_projekt LIKE ?
            OR kunde_nr LIKE ?
            ORDER BY erstellt_am DESC
        """
        pattern = f"%{search_term}%"
        df = pd.read_sql_query(query, conn, params=(pattern, pattern, pattern, pattern))
        conn.close()
        return df
    
    def update_monday_id(self, angebots_nr: str, monday_item_id: str):
        """Aktualisiert Monday Item ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE angebote 
            SET monday_item_id = ? 
            WHERE angebots_nr = ?
        """, (monday_item_id, angebots_nr))
        conn.commit()
        conn.close()
    
    def update_status(self, angebots_nr: str, status: str):
        """Aktualisiert Angebots-Status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE angebote 
            SET status = ? 
            WHERE angebots_nr = ?
        """, (status, angebots_nr))
        conn.commit()
        conn.close()
    
    def delete_quote(self, angebots_nr: str):
        """Löscht Angebot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM angebote WHERE angebots_nr = ?", (angebots_nr,))
        result = cursor.fetchone()
        
        if result:
            angebots_id = result[0]
            cursor.execute("DELETE FROM positionen WHERE angebots_id = ?", (angebots_id,))
            cursor.execute("DELETE FROM angebote WHERE id = ?", (angebots_id,))
            conn.commit()
        
        conn.close()
    
    def export_to_excel(self, filepath: str):
        """Exportiert nach Excel"""
        conn = self.get_connection()
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            pd.read_sql_query("SELECT * FROM angebote", conn).to_excel(writer, sheet_name='Angebote', index=False)
            pd.read_sql_query("SELECT * FROM positionen", conn).to_excel(writer, sheet_name='Positionen', index=False)
            
            stats = self.get_statistics()
            pd.DataFrame([stats['gesamt']]).to_excel(writer, sheet_name='Statistiken', index=False)
        
        conn.close()
