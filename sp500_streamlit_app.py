import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from io import BytesIO
import requests
import warnings
warnings.filterwarnings("ignore")

# --- RÉPARATION DU BUILTIN str ---
import builtins as _bi
def _restore_builtin_str():
    """
    Répare les cas où `str` a été redéfini (localement ou globalement) et où
    des libs (pandas/yfinance) échouent avec `'str' object is not callable`.
    """
    try:
        # Si un nom local 'str' masque le builtin, on le supprime
        if "str" in globals() and globals()["str"] is not _bi.str:
            del globals()["str"]
        # Si le builtin a été modifié, on le restaure en utilisant la classe de "".
        if (not callable(_bi.str)) or (not isinstance("", _bi.str)):
            _bi.str = ("").__class__
    except Exception as repair_err:
        st.error(f"Impossible de restaurer le builtin str: {repair_err}")
_restore_builtin_str()

# Sanity check visible
st.caption(f"`callable(str)` = {callable(_bi.str)}, `isinstance('', str)` = {isinstance('', _bi.str)}")

# --- APP ---
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

    # IMPORTANT : ne pas utiliser astype(str) si `str` a été écrasé
    symbols = df["Symbol"].astype("string").str.strip().tolist()

    # Adaptation pour yfinance (BRK.B -> BRK-B, BF.B -> BF-B, etc.)
    symbols = [s.replace(".", "-") for s in symbols]

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
    impor
