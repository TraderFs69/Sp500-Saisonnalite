import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from io import BytesIO
import requests
import warnings
import builtins
import traceback  # ✅ ajouté ici
warnings.filterwarnings("ignore")

# Vérifie si str a été écrasé
if (str is not builtins.str) or (not callable(str)):
    st.error("⚠️ Le nom `str` a été réassigné dans votre code. Renommez cette variable (ex.: `texte`).")

st.title("📈 Analyse de saisonnalité du S&P 500")

col1, col2, col3 = st.columns([1,1,1])
with col1:
    n_years = st.number_input("Nombre d'années à analyser", min_value=1, max_value=30, value=15)
with col2:
    end_year = st.number_input("Année de fin", min_value=2000, max_value=datetime.today().year, value=2024)
with col3:
    debug_limit = st.number_input("Limiter à N tickers (debug)", min_value=0, max_value=505, value=0, help="0 = tous")

start_mmdd = st.text_input("Date de début annuelle (MM-DD)", value="06-14")
end_mmdd = st.text_input("Date de fin annuelle (MM-DD)", value="10-30")

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
FALLBACK_CSV_PATH = None  # ex. "data/sp500_constituents.csv"

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_sp500_tickers() -> list[str]:
    headers = {
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    }
    try:
        r = requests.get(WIKI_URL, headers=headers, timeout=20)
        r.raise_for_status()
        tables = pd.read_html(r.text)
        df = tables[0]
    except Exception as e:
        if FALLBACK_CSV_PATH:
            st.warning(f"Wikipedia indisponible ({e}). Utilisation du fallback CSV.")
            df = pd.read_csv(FALLBACK_CSV_PATH)
            if "Symbol" not in df.columns:
                raise ValueError("Le CSV de fallback doit contenir une colonne 'Symbol'.")
        else:
            raise

    # ne pas utiliser astype(str) si str a été écrasé
    symbols = df["Symbol"].astype("string").str.strip().tolist()
    symbols = [s.replace(".", "-") for s in symbols]  # BRK.B → BRK-B
    return sorted(set(symbols))

def parse_mmdd(year: int, mmdd: str) -> pd.Timestamp:
    mm, dd = mmdd.split("-")
    return pd.Timestamp(year=int(year), month=int(mm), day=int(dd))

@st.cache_data(show_spinner=False)
def download_prices(ticker: str, start_year: int, end_year: int) -> pd.DataFrame:
    data = yf.download(
        ticker,
        start=f"{start_year}-01-01",
        end=f"{end_year}-12-31",
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    if data is None or data.empty:
        return pd.DataFrame()
    if "Adj Close" in data.columns:
        close = data["Adj Close"].rename("Close").to_frame()
    else:
        close = data["Close"].rename("Close").to_frame()
    # enlever tout timezone
    try:
        close.index = close.index.tz_convert(None)
    except Exception:
        try:
            close.index = close.index.tz_localize(None)
        except Exception:
            pass
    close["Date"] = close.index
    return close

if st.button("Lancer l'analyse"):
    start_year = end_year - n_years + 1
    years = list(range(start_year, end_year + 1))
    st.write(f"📅 Analyse du {start_mmdd} au {end_mmdd} pour chaque année de {start_year} à {end_year}")

    try:
        tickers = fetch_sp500_tickers()
    except Exception as e:
        st.error(f"Impossible de charger la liste du S&P 500 : {e}")
        st.stop()

    if debug_limit and debug_limit > 0:
        tickers = tickers[:int(debug_limit)]

    rendements_par_ticker = {}
    stats_summary = []

    progress_bar = st.progress(0)
    status_text = st.empty()
    first_trace_shown = False

    for i, ticker in enumerate(tickers):
        try:
            data = download_prices(ticker, start_year, end_year)
            if data.empty or "Close" not in data.columns:
                progress_bar.progress((i + 1) / len(tickers))
                status_text.text(f"{ticker}: pas de données. ({i + 1}/{len(tickers)})")
                continue

            rendements = {}
            for year in years:
                try:
                    start_date = parse_mmdd(year, start_mmdd)
                    end_date = parse_mmdd(year, end_mmdd)
                    df_period = data[(data["Date"] >= start_date) & (data["Date"] <= end_date)]
                    if len(df_period) < 2:
                        continue
                    prix_debut = df_period.iloc[0]["Close"]
                    prix_fin = df_period.iloc[-1]["Close"]
                    rendement = ((prix_fin / prix_debut) - 1) * 100.0
                    rendements[year] = rendement
                except Exception:
                    continue

            if len(rendements) >= 1:
                s = pd.Series(rendements, name="Rendement (%)").sort_index()
                stats_summary.append({
                    "Ticker": ticker,
                    "Moyenne (%)": round(s.mean(), 2),
                    "Médiane (%)": round(s.median(), 2),
                    "Écart-type (%)": round(s.std(), 2),
                    "% Années Positives": round((s > 0).sum() * 100.0 / len(s), 2),
                    "Nb Années": int(len(s)),
                })
                rendements_par_ticker[ticker] = s

        except Exception as e:
            st.warning(f"⚠️ Erreur pour {ticker} : {e}")
            if not first_trace_shown:
                st.code(traceback.format_exc())
                first_trace_shown = True

        progress_bar.progress((i + 1) / len(tickers))
        status_text.text(f"Analyse en cours... ({i + 1}/{len(tickers)})")

    if stats_summary:
        stats_df = pd.DataFrame(stats_summary).sort_values(by="Moyenne (%)", ascending=False)
        st.dataframe(stats_df, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            stats_df.to_excel(writer, sheet_name="Statistiques", index=False)
            for ticker, series in rendements_par_ticker.items():
                try:
                    df = pd.DataFrame({"Année": series.index, "Rendement (%)": series.values})
                    df.to_excel(writer, sheet_name=ticker[:31], index=False)
                except Exception:
                    pass

        st.download_button(
            label="📥 Télécharger le fichier Excel",
            data=output.getvalue(),
            file_name="rendements_saison_sp500.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ Aucune donnée suffisante pour créer un fichier.")

# Utilitaire : vider le cache si besoin
if st.button("🧹 Vider le cache (debug)"):
    st.cache_data.clear()
    st.success("Cache vidé.")
