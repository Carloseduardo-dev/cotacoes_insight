import yfinance as yf
import pandas as pd


def fetch_data(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Busca dados históricos usando yfinance e retorna um DataFrame válido."""
    try:
        # Forçar auto_adjust=False para evitar multi-index inesperado
        data = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    except Exception as e:
        print("❌ Erro ao baixar dados:", e)
        return pd.DataFrame()

    # Nenhum dado retornado
    if data is None or data.empty:
        print(f"⚠️ Nenhum dado retornado para {ticker}.")
        return pd.DataFrame()

    # Corrigir multi-index: pegar apenas colunas de nível superior se houver
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Garantir coluna 'Close'
    if "Close" not in data.columns:
        print(f"⚠️ Dados de {ticker} não contêm coluna 'Close'. Colunas disponíveis: {list(data.columns)}")
        return pd.DataFrame()
        
    # Verificar se há valores nulos na coluna 'Close' antes de usar dropna
    if data["Close"].isna().any():
        # Remover linhas vazias
        data = data.dropna(subset=["Close"])

    # Garantir índice datetime
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)

    return data