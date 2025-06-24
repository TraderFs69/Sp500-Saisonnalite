
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")
st.title("📊 Analyse saisonnière du S&P 500")

# Saisie utilisateur
n_years = st.number_input("Nombre d'années à analyser", min_value=1, value=15)
end_year = st.number_input("Année de fin", min_value=1900, max_value=datetime.today().year, value=2024)
start_mmdd = st.text_input("Date de début annuelle (MM-DD)", value="06-14")
end_mmdd = st.text_input("Date de fin annuelle (MM-DD)", value="10-30")

if st.button("Lancer l'analyse"):
    start_year = end_year - n_years + 1
    years = list(range(start_year, end_year + 1))
    st.info(f"📅 Analyse du {start_mmdd} au {end_mmdd} pour les années {start_year} à {end_year}")

    wiki_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        sp500_table = pd.read_html(wiki_url)[0]
        tickers = sp500_table['Symbol'].tolist()
    except:
        st.error("Impossible de récupérer la liste des tickers du S&P 500.")
        st.stop()

    rendements_par_ticker = {}
    stats_summary = []

    progress = st.progress(0)
    for i, ticker in enumerate(tickers):
        progress.progress((i + 1) / len(tickers))
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
                try:
                    start_date = f"{year}-{start_mmdd}"
                    end_date = f"{year}-{end_mmdd}"
                    df_period = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]
                    if len(df_period) < 2:
                        continue
                    prix_debut = df_period.iloc[0]['Close']
                    prix_fin = df_period.iloc[-1]['Close']
                    rendement = ((prix_fin / prix_debut) - 1) * 100
                    rendements[year] = rendement
                except:
                    continue

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
            continue

    if stats_summary:
        stats_df = pd.DataFrame(stats_summary).sort_values(by='Moyenne (%)', ascending=False)
        st.dataframe(stats_df)

        with pd.ExcelWriter("rendements_saison_sp500.xlsx") as writer:
            stats_df.to_excel(writer, sheet_name="Statistiques", index=False)
            for ticker, series in rendements_par_ticker.items():
                df = series.reset_index()
                if df.shape[1] == 2:
                    df.columns = ['Année', 'Rendement (%)']
                    df.to_excel(writer, sheet_name=ticker[:31], index=False)

        with open("rendements_saison_sp500.xlsx", "rb") as f:
            st.download_button("📥 Télécharger le fichier Excel", f, file_name="rendements_saison_sp500.xlsx")
    else:
        st.warning("❌ Aucune donnée exploitable")
