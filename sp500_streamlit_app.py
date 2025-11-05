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

    # --- Récupère la "close" de façon robuste ---
    # 1) privilégie Adj Close si dispo
    if "Adj Close" in data.columns:
        close_like = data["Adj Close"]
    else:
        close_like = data["Close"]

    # 2) Si c'est un DataFrame 1-colonne (ou MultiIndex), on prend la 1re colonne
    if isinstance(close_like, pd.DataFrame):
        if close_like.columns.nlevels > 1:
            # ex: colonnes MultiIndex (('Adj Close', ''), …) -> prendre la première colonne réelle
            first_col = close_like.columns[0]
            close_like = close_like[first_col]
        else:
            close_like = close_like.iloc[:, 0]

    # 3) Aplatir en 1D de façon sûre
    values_1d = pd.to_numeric(close_like, errors="coerce").to_numpy().ravel()

    close = pd.DataFrame({"Close": values_1d}, index=close_like.index)

    # --- Nettoie le timezone de l'index si présent ---
    try:
        close.index = close.index.tz_convert(None)
    except Exception:
        try:
            close.index = close.index.tz_localize(None)
        except Exception:
            pass

    close["Date"] = close.index
    return close
