import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from io import BytesIO
import requests
import warnings
import traceback
warnings.filterwarnings("ignore")

# ---------------- UI ----------------
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

# ---------------- Helpers ----------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_sp500_tickers() -> list:
    """
    Charge la liste S&P 500 :
    1) Wikipedia (?action=render) avec User-Agent
    2) Wikipedia standard
    3) Fallback Slickcharts
    Renvoie des tickers formatés pour yfinance (BRK.B -> BRK-B).
    """
    import re

    wiki_urls = [
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies?action=render",
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    ]
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://en.wikipedia.org/",
    }

    def extract_symbols_from_tables(tables: list[pd.DataFrame]) -> list[str] | None:
        # Choisir la première table qui possède une colonne contenant "Symbol"
        for df in tables:
            cols = [str(c).strip() for c in df.columns]
            if any(re.search(r"\bSymbol\b", c, flags=re.I) for c in cols):
                sym_col = [c for c in df.columns if re.search(r"\bSymbol\b", str(c), re.I)][0]
                symbols = (
                    df[sym_col]
                    .astype("string")
                    .str.strip()
                    .dropna()
                    .tolist()
                )
                return symbols
        return None

    # 1 & 2) Tentatives Wikipedia
    for url in wiki_urls:
        try:
            r = requests.get(url, headers=headers, timeout=25)
            r.raise_for_status()
            tables = pd.read_html(r.text, flavor="lxml")
            symbols = extract_symbols_from_tables(tables)
            if symbols:
                symbols = [s.replace(".", "-") for s in symbols]  # BRK.B -> BRK-B
                return sorted(set([s for s in symbols if s and s != "nan"]))
        except Exception:
            continue  # on tente l'URL suivante

    # 3) Fallback Slickcharts
    try:
        sc_headers = headers | {"Referer": "https://www.slickcharts.com/sp500"}
        sc = requests.get("https://www.slickcharts.com/sp500", headers=sc_headers, timeout=20)
        sc.raise_for_status()
        tables = pd.read_html(sc.text)
        symbols = None
        for df in tables:
            if "Symbol" in df.columns:
                symbols = (
                    df["Symbol"].astype("string").str.strip().dropna().tolist()
                )
                break
        if symbols:
            symbols = [s.replace(".", "-") for s in symbols]
            return sorted(set(symbols))
    except Exception:
        pass

    # 4) CSV local facultatif si tu en as un
    if FALLBACK_CSV_PATH:
        st.warning("Sources en ligne indisponibles. Utilisation du CSV local.")
        df = pd.read_csv(FALLBACK_CSV_PATH)
        if "Symbol" not in df.columns:
            raise ValueError("Le CSV de fallback doit contenir une colonne 'Symbol'.")
        symbols = df["Symbol"].astype("string").str.strip().tolist()
        symbols = [s.replace(".", "-") for s in symbols]
        return sorted(set(symbols))

    # Si tout échoue :
    raise RuntimeError("Impossible de récupérer la liste S&P 500 depuis Wikipedia/Slickcharts.")

def parse_mmdd(year: int, mmdd: str) -> pd.Timestamp:
    mm, dd = mmdd.split("-")
    return pd.Timestamp(year=int(year), month=int(mm), day=int(dd))

@st.cache_data(show_spinner=False)
def download_prices(ticker: str, start_year: int, end_year: int) -> pd.DataFrame:
    """Télécharge l’historique et renvoie un DataFrame avec colonnes: Close, Date."""
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

    # Choisir la série 'close' de façon robuste
    close_like = data["Adj Close"] if "Adj Close" in data.columns else data["Close"]
    if isinstance(close_like, pd.DataFrame):
        # MultiIndex ou DataFrame 1-colonne -> prendre la première vraie colonne
        close_like = close_like.iloc[:, 0]

    # Aplatir proprement en 1D
    values_1d = pd.to_numeric(close_like, errors="coerce").to_numpy().ravel()
    close = pd.DataFrame({"Close": values_1d}, index=close_like.index)

    # Nettoyage timezone
    try:
        close.index = close.index.tz_convert(None)
    except Exception:
        try:
            close.index = close.index.tz_localize(None)
        except Exception:
            pass

    close["Date"] = close.index
    return close

# ---------------- Main ----------------
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
                    rend = ((prix_fin / prix_debut) - 1) * 100.0
                    rendements[year] = rend
                except Exception:
                    continue

            if rendements:
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
