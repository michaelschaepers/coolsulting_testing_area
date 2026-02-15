# ==========================================
# DATEI: coolmatch_analytics.py
# VERSION: 7.0
# AUTOR: Michael Schäpers, coolsulting
# BESCHREIBUNG: Analytics Dashboard mit Plotly Charts
# ==========================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from coolmatch_database import CoolMatchDatabase
from coolmatch_config import COLOR_BLUE_HEX, COLOR_DARK_GRAY, COLOR_BLUE

class CoolMatchAnalytics:
    """Erstellt interaktive Dashboards und Visualisierungen"""
    
    def __init__(self, db: CoolMatchDatabase):
        self.db = db
    
    def render_dashboard(self):
        """Hauptseite des Analytics Dashboards"""
        st.markdown("## 📊 Analytics Dashboard")
        st.markdown("---")
        
        # Statistiken laden
        stats = self.db.get_statistics()
        
        # KPI Cards
        self._render_kpi_cards(stats['gesamt'])
        
        st.markdown("---")
        
        # Charts in 2 Spalten
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_monthly_chart(stats['monthly'])
            st.markdown("---")
            self._render_category_distribution(stats['categories'])
        
        with col2:
            self._render_top_products(stats['top_products'])
            st.markdown("---")
            self._render_status_overview(stats['status'])
    
    def _render_kpi_cards(self, gesamt_stats: dict):
        """Zeigt KPI-Karten an"""
        cols = st.columns(4)
        
        kpis = [
            ("📝 Angebote", f"{gesamt_stats['anzahl']:.0f}", "Total"),
            ("💰 Volumen", f"{gesamt_stats['summe']:,.0f} €", "Brutto"),
            ("📊 Durchschnitt", f"{gesamt_stats['durchschnitt']:,.0f} €", "Pro Angebot"),
            ("🎯 Max. Angebot", f"{gesamt_stats['max']:,.0f} €", "Höchster Wert")
        ]
        
        for col, (title, value, subtitle) in zip(cols, kpis):
            with col:
                st.markdown(f"""
                    <div style='
                        background: white;
                        padding: 20px;
                        border-radius: 10px;
                        border-left: 4px solid {COLOR_BLUE_HEX};
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    '>
                        <div style='font-size: 14px; color: {COLOR_DARK_GRAY}; margin-bottom: 5px;'>
                            {title}
                        </div>
                        <div style='font-size: 24px; font-weight: bold; color: {COLOR_BLUE_HEX};'>
                            {value}
                        </div>
                        <div style='font-size: 12px; color: #999;'>
                            {subtitle}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    def _render_monthly_chart(self, df_monthly: pd.DataFrame):
        """Monatliche Umsatzentwicklung"""
        st.markdown("### 📈 Monatliche Entwicklung")
        
        if df_monthly.empty:
            st.info("Noch keine Daten verfügbar")
            return
        
        # Chronologische Reihenfolge
        df_monthly = df_monthly.iloc[::-1]
        
        fig = go.Figure()
        
        # Balken für Anzahl
        fig.add_trace(go.Bar(
            x=df_monthly['monat'],
            y=df_monthly['anzahl'],
            name='Anzahl',
            marker_color=COLOR_BLUE_HEX,
            yaxis='y'
        ))
        
        # Linie für Summe
        fig.add_trace(go.Scatter(
            x=df_monthly['monat'],
            y=df_monthly['summe'],
            name='Volumen (€)',
            line=dict(color=COLOR_DARK_GRAY, width=3),
            yaxis='y2'
        ))
        
        fig.update_layout(
            yaxis=dict(title='Anzahl'),
            yaxis2=dict(title='Volumen (€)', overlaying='y', side='right'),
            hovermode='x unified',
            height=350,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_top_products(self, df_products: pd.DataFrame):
        """Top 15 Produkte"""
        st.markdown("### 🏆 Top Produkte")
        
        if df_products.empty:
            st.info("Noch keine Produkte erfasst")
            return
        
        # Kürze Beschreibungen
        df_products['short_desc'] = df_products['beschreibung'].str[:30] + '...'
        
        fig = go.Figure(go.Bar(
            x=df_products['anzahl'][:10],
            y=df_products['short_desc'][:10],
            orientation='h',
            marker_color=COLOR_BLUE_HEX,
            text=df_products['anzahl'][:10],
            textposition='outside'
        ))
        
        fig.update_layout(
            xaxis_title='Anzahl',
            yaxis_title='',
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detaillierte Tabelle
        with st.expander("📋 Produktdetails"):
            display_df = df_products[['artikel_nr', 'beschreibung', 'kategorie', 'anzahl', 'gesamt_menge', 'durchschnittspreis']].copy()
            display_df.columns = ['Artikel', 'Beschreibung', 'Kategorie', 'Verkäufe', 'Menge', 'Ø Preis']
            display_df['Ø Preis'] = display_df['Ø Preis'].apply(lambda x: f"{x:,.2f} €")
            st.dataframe(display_df, hide_index=True, use_container_width=True)
    
    def _render_category_distribution(self, df_categories: pd.DataFrame):
        """Kategorie-Verteilung"""
        st.markdown("### 🎯 Kategorie-Verteilung")
        
        if df_categories.empty:
            st.info("Noch keine Kategorien erfasst")
            return
        
        fig = go.Figure(go.Pie(
            labels=df_categories['kategorie'],
            values=df_categories['umsatz'],
            hole=0.4,
            marker=dict(colors=[COLOR_BLUE_HEX, '#6BC4E8', '#A0D8F1', '#D0EBFA'])
        ))
        
        fig.update_layout(
            height=350,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_status_overview(self, df_status: pd.DataFrame):
        """Status-Übersicht"""
        st.markdown("### 📊 Status-Übersicht")
        
        if df_status.empty:
            st.info("Noch keine Status-Daten")
            return
        
        fig = go.Figure(go.Bar(
            x=df_status['status'],
            y=df_status['summe'],
            marker_color=COLOR_BLUE_HEX,
            text=df_status['anzahl'].apply(lambda x: f"{x:.0f} Ang."),
            textposition='outside'
        ))
        
        fig.update_layout(
            xaxis_title='Status',
            yaxis_title='Volumen (€)',
            height=350,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_quote_history(self):
        """Angebots-Historie mit Suchfunktion"""
        st.markdown("## 📚 Angebots-Historie")
        st.markdown("---")
        
        # Suchfeld und Buttons
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            search_term = st.text_input("🔍 Suche nach Kunde, Projekt, Angebots-Nr...", "")
        with col2:
            if st.button("🔄 Aktualisieren", use_container_width=True):
                st.rerun()
        with col3:
            if st.button("📥 Export Excel", use_container_width=True):
                try:
                    export_path = f"export_angebote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    self.db.export_to_excel(export_path)
                    st.success(f"✅ Exportiert: {export_path}")
                except Exception as e:
                    st.error(f"❌ Export-Fehler: {e}")
        
        # Daten laden
        if search_term:
            df_quotes = self.db.search_quotes(search_term)
        else:
            df_quotes = self.db.get_all_quotes(limit=100)
        
        if df_quotes.empty:
            st.info("Keine Angebote gefunden")
            return
        
        # Formatierung
        display_df = df_quotes[[
            'angebots_nr', 'kunde_name', 'kunde_projekt', 'erstellt_am',
            'summe_brutto', 'status', 'bearbeiter'
        ]].copy()
        
        display_df.columns = [
            'Angebots-Nr', 'Kunde', 'Projekt', 'Erstellt',
            'Summe (€)', 'Status', 'Bearbeiter'
        ]
        
        display_df['Erstellt'] = pd.to_datetime(display_df['Erstellt']).dt.strftime('%d.%m.%Y')
        display_df['Summe (€)'] = display_df['Summe (€)'].apply(lambda x: f"{x:,.2f}")
        
        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            height=500
        )
        
        # Details zu ausgewähltem Angebot
        st.markdown("---")
        selected_nr = st.selectbox(
            "Angebot im Detail anzeigen:",
            options=[''] + df_quotes['angebots_nr'].tolist()
        )
        
        if selected_nr:
            self._render_quote_details(selected_nr)
    
    def _render_quote_details(self, angebots_nr: str):
        """Zeigt Details eines spezifischen Angebots"""
        quote_data = self.db.get_quote_by_nr(angebots_nr)
        
        if not quote_data:
            st.error("Angebot nicht gefunden")
            return
        
        header = quote_data['header']
        positions = quote_data['positions']
        
        # Header-Infos
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**Kunde:** {header[2]}")
            st.markdown(f"**Projekt:** {header[3]}")
        
        with col2:
            st.markdown(f"**Erstellt:** {header[5]}")
            st.markdown(f"**Bearbeiter:** {header[7]}")
        
        with col3:
            st.markdown(f"**Status:** {header[16]}")
            st.markdown(f"**Summe:** {header[10]:,.2f} €")
        
        st.markdown("---")
        
        # Positionen
        st.markdown("**Positionen:**")
        
        df_pos = pd.DataFrame(positions, columns=[
            'id', 'angebots_id', 'position_nr', 'typ', 'artikel_nr',
            'beschreibung', 'menge', 'einzelpreis', 'rabatt', 'gesamt', 'notiz'
        ])
        
        display_pos = df_pos[['position_nr', 'typ', 'artikel_nr', 'beschreibung', 'menge', 'einzelpreis', 'rabatt', 'gesamt']]
        display_pos.columns = ['Pos', 'Typ', 'Artikel', 'Beschreibung', 'Menge', 'Preis', 'Rabatt %', 'Gesamt']
        
        st.dataframe(display_pos, hide_index=True, use_container_width=True)
        
        # Status ändern
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            new_status = st.selectbox(
                "Status ändern:",
                ['Erstellt', 'Gesendet', 'Angenommen', 'Abgelehnt', 'Storniert'],
                index=['Erstellt', 'Gesendet', 'Angenommen', 'Abgelehnt', 'Storniert'].index(header[16])
            )
        
        with col2:
            st.write(" ")
            st.write(" ")
            if st.button("💾 Status speichern", use_container_width=True):
                self.db.update_status(angebots_nr, new_status)
                st.success("✅ Status aktualisiert!")
                st.rerun()
