# Author: Siddhant Shukla <sidz0124@gmail.com>
"""SEBI F&O curbs (20-Nov-2024) natural experiment: 6M before vs 6M after vs latest 6M."""
import numpy as np
import pandas as pd
from scipy import stats

import config as C
from src.analytics import common as cm

CR = 1e7


def build_weekly() -> pd.DataFrame:
    seg = pd.read_parquet(C.PROCESSED / "res_segments.parquet")
    part = pd.read_parquet(C.PROCESSED / "res_participants.parquet")
    surf = pd.read_parquet(C.PROCESSED / "res_surface_agg.parquet")
    dte = pd.read_parquet(C.PROCESSED / "res_dte_idx.parquet")
    df = pd.DataFrame(index=seg.index)
    df["Index option contracts (mn)"] = seg["contracts_idx"] / 1e6
    df["Index option premium (Rs cr)"] = seg["premium_idx"] / CR
    df["Index option notional (Rs lakh cr)"] = seg["und_notional_idx"] / 1e12
    df["Stock option notional (Rs '000 cr)"] = seg["und_notional_stk"] / 1e10
    df["Stock option premium (Rs cr)"] = seg["premium_stk"] / CR
    df["Client contracts, index opt (mn)"] = part["total_contracts_idx"] * part["share_Client_idx"] / 1e6
    df["Client share, index options"] = part["share_Client_idx"]
    df["Client share, stock options"] = part["share_Client_stk"]
    df["0-1D share of index notional"] = dte["0-1D"] / dte.sum(axis=1)
    df["NIFTY 30D ATM IV"] = surf["iv30_NIFTY"]
    df["NIFTY 30D skew"] = surf["skew30_NIFTY"]
    df["Top30 skew"] = surf["skew30_Top30"]
    df["Top30 VRP (IV/RV)"] = surf["vrp_median_Top30"]
    df["Rest VRP (IV/RV)"] = surf["vrp_median_Rest"]
    return df


def run() -> dict:
    df = build_weekly()
    t0 = pd.Timestamp(C.SEBI_CURB_DATE)
    pre = df[(df.index >= t0 - pd.DateOffset(months=6)) & (df.index < t0)]
    post = df[(df.index >= t0) & (df.index < t0 + pd.DateOffset(months=6))]
    latest = df.iloc[-26:]
    rows = []
    for c in df.columns:
        a, b = pre[c].dropna(), post[c].dropna()
        t, p = stats.ttest_ind(a, b, equal_var=False) if len(a) > 3 and len(b) > 3 else (np.nan, np.nan)
        rows.append({"metric": c, "pre_6m": a.mean(), "post_6m": b.mean(), "latest_6m": latest[c].mean(),
                     "chg_post_pct": (b.mean() / a.mean() - 1) * 100, "chg_latest_pct": (latest[c].mean() / a.mean() - 1) * 100,
                     "p_value": p})
    tab = pd.DataFrame(rows).set_index("metric")
    tab.to_csv(C.TABLES / "sebi_event_study.csv")
    df.to_parquet(C.PROCESSED / "res_event_weekly.parquet")
    cm.save_result("events", tab.round(4).to_dict(orient="index"))
    return tab


if __name__ == "__main__":
    print(run().round(3).to_string())
