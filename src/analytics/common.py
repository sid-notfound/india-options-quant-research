# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Shared loaders and helpers for the analytics modules."""
import json
from functools import lru_cache

import numpy as np
import pandas as pd

import config as C

RESULTS_JSON = C.TABLES / "results.json"


def save_result(key: str, value) -> None:
    data = json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else {}
    data[key] = value
    RESULTS_JSON.write_text(json.dumps(data, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def load_results() -> dict:
    return json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else {}


@lru_cache(None)
def calendar() -> pd.DataFrame:
    return pd.read_csv(C.PROCESSED / "sample_calendar.csv", parse_dates=["date"])


def weekly_dates() -> pd.DatetimeIndex:
    cal = calendar()
    return pd.DatetimeIndex(sorted(cal.loc[cal["kind"] == "weekly", "date"].unique()))


def entry_dates() -> pd.DatetimeIndex:
    cal = calendar()
    return pd.DatetimeIndex(sorted(cal.loc[cal["kind"] == "entry", "date"].unique()))


@lru_cache(None)
def panel(columns: tuple = None) -> pd.DataFrame:
    return pd.read_parquet(C.PROCESSED / "fo_panel.parquet", columns=list(columns) if columns else None)


@lru_cache(None)
def activity() -> pd.DataFrame:
    a = pd.read_parquet(C.PROCESSED / "activity.parquet")
    return a.fillna({c: 0 for c in a.columns if c.split("_")[0] in ("contracts", "oi", "premium", "dadj", "und")
                     and c != "und"})


@lru_cache(None)
def surface_cm() -> pd.DataFrame:
    return pd.read_parquet(C.PROCESSED / "surface_cm.parquet")


@lru_cache(None)
def surface_expiry() -> pd.DataFrame:
    return pd.read_parquet(C.PROCESSED / "surface_expiry.parquet")


@lru_cache(None)
def prices():
    close = pd.read_parquet(C.RAW_PRICES / "close.parquet").sort_index()
    vol = pd.read_parquet(C.RAW_PRICES / "volume.parquet").sort_index()
    return close, vol


@lru_cache(None)
def sectors() -> pd.Series:
    from src.data.universe import sector_map
    return sector_map()


def stock_symbols() -> list:
    a = activity()
    return sorted(set(a["symbol"]) - set(C.INDEX_SYMBOLS))


@lru_cache(None)
def traded_value_weights() -> pd.DataFrame:
    """Trailing 63-day average traded value (Rs) - used as a market-cap proxy for weighting."""
    close, vol = prices()
    return (close * vol).rolling(63, min_periods=20).mean()


def groups() -> dict:
    p = C.PROCESSED / "groups.json"
    return json.loads(p.read_text())


def asof(df: pd.DataFrame, dates) -> pd.DataFrame:
    """Row of a daily (date-indexed) frame as of each date (last available on or before)."""
    return df.reindex(df.index.union(dates)).ffill().reindex(dates)


def log_returns(close: pd.DataFrame) -> pd.DataFrame:
    r = np.log(close).diff()
    return r.where(r.abs() < 0.4)  # drop split/bonus artefacts


def realized_vol_forward(close: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    r = log_returns(close)
    rv = r.rolling(window, min_periods=int(window * 0.8)).std() * np.sqrt(C.TRADING_DAYS)
    return rv.shift(-window)


def realized_vol_trailing(close: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    r = log_returns(close)
    return r.rolling(window, min_periods=int(window * 0.8)).std() * np.sqrt(C.TRADING_DAYS)


def adjusted_realized_vol(close: pd.DataFrame, window: int = 63, k: float = 3.0) -> pd.DataFrame:
    """Outlier-robust RV: clip each return at median +/- k * 1.4826 * MAD of the trailing window."""
    r = log_returns(close)
    med = r.rolling(window, min_periods=40).median()
    mad = (r - med).abs().rolling(window, min_periods=40).median() * 1.4826
    clipped = r.clip(med - k * mad, med + k * mad)
    return clipped.rolling(window, min_periods=40).std() * np.sqrt(C.TRADING_DAYS)


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    m = values.notna() & weights.notna() & (weights > 0)
    if m.sum() == 0:
        return np.nan
    return float(np.average(values[m], weights=weights[m]))
