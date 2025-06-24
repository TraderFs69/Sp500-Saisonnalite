
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from io import BytesIO

st.title("📊 Analyse saisonnière S&P 500")

n_years = st.number_input("Nombre d'années à analyser", min_value=1, max_value=30, value=15)
end_year = st.number_input("Année de fin", min_value=2000, max_value=datetime.now().year, value=2024)
start_mmdd = st.text_input("Date de début annuelle (MM-DD)", value="06-14")
end_mmdd = st.text_input("Date de fin annuelle (MM-DD)", value="10-30")

if st.button("Lancer l'analyse"):
    start_year = end_year - n_years + 1
    years = list(range(start_year, end_year + 1))
    wiki_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tickers = pd.read_html(wiki_url)[0]['Symbol'].tolist()

    rendements_par_ticker = {}
    stats_summary = []

    with st.spinner("Téléchargement des données..."):
        for ticker in tickers:
            try:
                data = yf.download(ticker, start=f"{start_year}-01-01", end=f"{end_year}-12-31", progress=False, auto_adjust=False)
                if data.empty or 'Adj Close' not in data.columns:
                    continue

                data = data[['Adj Close']].copy()
                data.columns = ['Close']
                data['Date'] = data.index
                data['Year'] = data['Date'].dt.year
                data['MM-DD'] = data['Date'].dt.strftime('%m-%d')

                rendements = {}
                for year in years:
                    start_date = f"{year}-{start_mmdd}"
                    end_date = f"{year}-{end_mmdd}"
                    df_period = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]
                    if len(df_period) < 2:
                        continue
                    prix_debut = df_period.iloc[0]['Close']
                    prix_fin = df_period.iloc[-1]['Close']
                    rendement = ((prix_fin / prix_debut) - 1) * 100
                    rendements[year] = rendement

                if len(rendements) >= 3:
                    df_rend = pd.Series(rendements).sort_index()
                    moyenne = df_rend.mean()
                    mediane = df_rend.median()
                    ecart_type = df_rend.std()
                    pourcentage_positif = (df_rend > 0).sum() / len(df_rend) * 100

                    rendements_par_ticker[ticker] = df_rend
                    stats_summary.append({
                        'Ticker': ticker,
                        'Moyenne (%)': round(moyenne, 2),
                        'Médiane (%)': round(mediane, 2),
                        'Écart-type (%)': round(ecart_type, 2),
                        '% Années Positives': round(pourcentage_positif, 2),
                        'Nb Années': len(df_rend)
                    })
            except Exception as e:
                st.warning(f"⚠️ Erreur pour {ticker} : {e}")

    if stats_summary:
        stats_df = pd.DataFrame(stats_summary).sort_values(by='Moyenne (%)', ascending=False)

        # Génération Excel
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            stats_df.to_excel(writer, sheet_name="Statistiques", index=False)
            for ticker, series in rendements_par_ticker.items():
                df = pd.DataFrame({'Année': series.index, 'Rendement (%)': series.values})
                df.to_excel(writer, sheet_name=ticker[:31], index=False)

        st.success("✅ Analyse terminée")
        st.download_button(label="📥 Télécharger le fichier Excel",
                           data=buffer.getvalue(),
                           file_name="rendements_saison_sp500.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.error("❌ Aucune donnée exploitable")
