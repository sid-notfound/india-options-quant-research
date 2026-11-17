# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Daily close / volume from Yahoo Finance for the F&O universe and indices."""
import pandas as pd
import yfinance as yf

import config as C

yf.set_tz_cache_location(str(C.RAW_PRICES / "yf_cache"))


def yahoo_ticker(sym: str) -> str:
    if sym in C.YAHOO_INDEX:
        return C.YAHOO_INDEX[sym]
    return C.YAHOO_RENAMES.get(sym, sym) + ".NS"


def download(symbols, chunk: int = 40) -> None:
    close_p, vol_p = C.RAW_PRICES / "close.parquet", C.RAW_PRICES / "volume.parquet"
    tickers = {s: yahoo_ticker(s) for s in symbols}
    closes, vols = [], []
    items = list(tickers.items())
    for i in range(0, len(items), chunk):
        part = dict(items[i:i + chunk])
        d = yf.download(list(set(part.values())), start=str(C.START - pd.Timedelta(days=150)),
                        end=str(C.END + pd.Timedelta(days=1)), auto_adjust=False,
                        progress=False, threads=False, group_by="column")
        if d.empty:
            continue
        cl, vo = d["Close"], d["Volume"]
        if isinstance(cl, pd.Series):
            cl, vo = cl.to_frame(list(part.values())[0]), vo.to_frame(list(part.values())[0])
        for sym, tk in part.items():
            if tk in cl.columns and cl[tk].notna().sum() > 20:
                closes.append(cl[tk].rename(sym))
                vols.append(vo[tk].rename(sym))
        print(f"[prices] {min(i + chunk, len(items))}/{len(items)}")
    close = pd.concat(closes, axis=1)
    vol = pd.concat(vols, axis=1)
    close.index = pd.to_datetime(close.index).tz_localize(None)
    vol.index = close.index
    close = close.loc[:, ~close.columns.duplicated()]
    vol = vol.loc[:, ~vol.columns.duplicated()]
    close.to_parquet(close_p)
    vol.to_parquet(vol_p)
    missing = sorted(set(symbols) - set(close.columns))
    print(f"[prices] got {close.shape[1]} series; missing {len(missing)}: {missing[:40]}")


def load():
    close = pd.read_parquet(C.RAW_PRICES / "close.parquet")
    vol = pd.read_parquet(C.RAW_PRICES / "volume.parquet")
    return close, vol
