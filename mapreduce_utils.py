from multiprocessing import Pool, cpu_count, freeze_support
from functools import reduce
import numpy as np
import pandas as pd

# Inicializar suporte para multiprocessing no Windows
freeze_support()

# --- Map functions ---

def map_close(series_chunk):
    """Map: retorna lista de valores de fechamento do chunk."""
    return list(series_chunk)


# --- Reduce functions ---

def reduce_concat(lists):
    return reduce(lambda a, b: a + b, lists, [])


def compute_stats_from_list(values):
    arr = np.array(values, dtype=float)
    return {
        "mean": float(np.nanmean(arr)),
        "min": float(np.nanmin(arr)),
        "max": float(np.nanmax(arr)),
        "std": float(np.nanstd(arr, ddof=1)),
    }


# --- Orquestrador MapReduce local ---

def chunkify(seq, n_chunks):
    """Divide uma sequência em n_chunks de maneira balanceada."""
    seq = list(seq)
    k, m = divmod(len(seq), n_chunks)
    chunks = [seq[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n_chunks)]
    return [c for c in chunks if c]

if __name__ == "__main__":
    freeze_support()


def calculate_volatility(returns_series):
    """Calcula a volatilidade anualizada dos retornos."""
    # Assumindo retornos diários, multiplicamos por sqrt(252) para anualizar
    return float(np.std(returns_series, ddof=1) * np.sqrt(252))


def calculate_cumulative_return(returns_series):
    """Calcula o retorno cumulativo a partir da série de retornos."""
    return float((1 + returns_series).prod() - 1)


def calculate_max_drawdown(close_series):
    """Calcula o máximo drawdown da série de preços."""
    # Calcula o pico acumulado (máximo até o momento)
    peak = close_series.cummax()
    # Calcula o drawdown como (valor atual / pico - 1)
    drawdown = close_series / peak - 1
    # Retorna o valor mínimo (maior queda)
    return float(drawdown.min())


def map_reduce_stats(df: pd.DataFrame, metrics=None, moving_average_days: int = 10):
    """
    Executa um MapReduce local sobre a série de preços de fechamento.
    Retorna um dicionário com as métricas e séries calculadas.
    """
    # Garantir que freeze_support seja chamado no módulo principal
    if __name__ == "__main__":
        freeze_support()
        
    if metrics is None:
        metrics = ["mean", "min", "max"]

    close_series = df["Close"].dropna()
    n_workers = min(cpu_count(), 4) or 1
    chunks = chunkify(close_series.values, n_workers)

    results = {}

    with Pool(processes=n_workers) as pool:
        mapped = pool.map(map_close, chunks)

    all_values = reduce_concat(mapped)

    # Estatísticas
    stats = compute_stats_from_list(all_values)
    for k in ["mean", "min", "max", "std"]:
        if k in metrics:
            results[k] = stats.get(k)

    # Retornos diários (map/reduce)
    returns_series = None

    if any(m in metrics for m in ["returns", "volatility", "cumulative_return"]):
        returns_series = close_series.pct_change().dropna()

        if "returns" in metrics:
            results["returns"] = returns_series
    
    # Volatilidade (anualizada)
    if "volatility" in metrics and returns_series is not None:
        results["volatility"] = calculate_volatility(returns_series)
    
    # Retorno cumulativo
    if "cumulative_return" in metrics and returns_series is not None:
        results["cumulative_return"] = calculate_cumulative_return(returns_series)
    
    # Máximo drawdown
    if "max_drawdown" in metrics:
        results["max_drawdown"] = calculate_max_drawdown(close_series)

    # Moving average — calculado globalmente
    if "moving_average" in metrics:
        results[f"ma_{moving_average_days}"] = close_series.rolling(window=moving_average_days).mean()

    return results
