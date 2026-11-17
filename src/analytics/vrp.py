# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Skew, term structure and VRP for Top-30 vs Rest (U.S. study Figs 17-20 analogue)."""
import numpy as np
import pandas as pd

import config as C
from src.analytics import common as cm


def stock_metrics() -> pd.DataFrame:
    """Per (weekly date, stock): iv30, skew30, term, forward RV, VRP ratio, weight, group."""
    s = cm.surface_cm()
    s = s[s["date"].isin(cm.weekly_dates())].copy()
    close, _ = cm.prices()
    rv_fwd = cm.realized_vol_forward(close, 21)
    rv_tr = cm.realized_vol_trailing(close, 21)
    w = cm.traded_value_weights()

    def lookup(frame):
        st = frame.stack()
        st.index.names = ["date", "symbol"]
        return st

    keys = pd.MultiIndex.from_frame(s[["date", "symbol"]])
    dates = pd.DatetimeIndex(sorted(s["date"].unique()))
    s["rv_fwd"] = lookup(cm.asof(rv_fwd, dates)).reindex(keys).values
    s["rv_trail"] = lookup(cm.asof(rv_tr, dates)).reindex(keys).values
    s["w"] = lookup(cm.asof(w, dates)).reindex(keys).values
    s["vrp"] = s["iv30"] / s["rv_fwd"]
    s["vrp_diff"] = s["iv30"] - s["rv_fwd"]
    g = cm.groups()
    s["group"] = np.where(s["symbol"].isin(g["top"]), "Top30",
                          np.where(s["symbol"].isin(C.INDEX_SYMBOLS), "Index", "Rest"))
    # clip extreme surface outliers
    s.loc[~s["skew30"].between(-0.6, 0.8), "skew30"] = np.nan
    s.loc[~s["term"].between(0.5, 1.8), "term"] = np.nan
    s.loc[~s["vrp"].between(0.2, 5), "vrp"] = np.nan
    s.to_parquet(C.PROCESSED / "res_stock_metrics.parquet", index=False)
    return s


def aggregate(s: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (d, grp), x in s[s["group"] != "Index"].groupby(["date", "group"]):
        rows.append({
            "date": d, "group": grp,
            "iv30": cm.weighted_mean(x["iv30"], x["w"]),
            "skew30": cm.weighted_mean(x["skew30"], x["w"]),
            "term": cm.weighted_mean(x["term"], x["w"]),
            "vrp_wavg": cm.weighted_mean(x["vrp"], x["w"]),
            "vrp_median": x["vrp"].median(),
            "vrp_diff": cm.weighted_mean(x["vrp_diff"], x["w"]),
            "rv_fwd": cm.weighted_mean(x["rv_fwd"], x["w"]),
        })
    a = pd.DataFrame(rows).pivot(index="date", columns="group")
    a.columns = [f"{m}_{g}" for m, g in a.columns]
    idx = s[s["symbol"] == "NIFTY"].set_index("date")[["iv30", "skew30", "term", "rv_fwd", "vrp"]]
    a = a.join(idx.add_suffix("_NIFTY"))
    bn = s[s["symbol"] == "BANKNIFTY"].set_index("date")[["iv30", "vrp"]]
    a = a.join(bn.add_suffix("_BANKNIFTY"))
    vix = cm.prices()[0].get("INDIAVIX")
    if vix is not None:
        a["indiavix"] = cm.asof(vix.to_frame(), a.index).iloc[:, 0] / 100
    return a


def run() -> dict:
    s = stock_metrics()
    a = aggregate(s)
    a.to_parquet(C.PROCESSED / "res_surface_agg.parquet")
    peak = slice(*C.PEAK_PERIOD)
    st = {}
    for m in ("skew30", "term", "vrp_median", "iv30", "vrp_diff"):
        for g in ("Top30", "Rest"):
            col = f"{m}_{g}"
            st[f"{col}_2020"] = a.loc["2020", col].mean()
            st[f"{col}_peak"] = a.loc[peak, col].mean()
            st[f"{col}_full"] = a[col].mean()
            st[f"{col}_last6m"] = a[col].dropna().iloc[-26:].mean()
    for m in ("iv30", "vrp", "skew30"):
        st[f"{m}_NIFTY_full"] = a[f"{m}_NIFTY"].mean()
        st[f"{m}_NIFTY_peak"] = a.loc[peak, f"{m}_NIFTY"].mean()
    st["share_stocks_negative_skew"] = float((s.loc[s["group"] != "Index", "skew30"] < 0).mean())
    cm.save_result("surface", st)
    return st


if __name__ == "__main__":
    print(run())
