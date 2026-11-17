# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Performance statistics for periodic strategy returns."""
import numpy as np
import pandas as pd


def nav(returns: pd.Series, start: float = 100.0) -> pd.Series:
    return start * (1 + returns.fillna(0)).cumprod()


def stats(returns: pd.Series, periods_per_year: float) -> dict:
    r = returns.dropna()
    if len(r) == 0:
        return {}
    n = nav(r, 1.0)
    years = len(r) / periods_per_year
    cagr = n.iloc[-1] ** (1 / years) - 1 if n.iloc[-1] > 0 else np.nan
    vol = r.std(ddof=1) * np.sqrt(periods_per_year)
    dd = (n / n.cummax() - 1).min()
    return {
        "CAGR": cagr,
        "Ann. vol": vol,
        "Sharpe": (r.mean() * periods_per_year) / vol if vol > 0 else np.nan,
        "Max drawdown": dd,
        "Hit rate": float((r > 0).mean()),
        "Worst period": r.min(),
        "Best period": r.max(),
        "Periods": len(r),
    }


def stats_table(rets: pd.DataFrame, periods_per_year: float) -> pd.DataFrame:
    return pd.DataFrame({c: stats(rets[c], periods_per_year) for c in rets.columns}).T
