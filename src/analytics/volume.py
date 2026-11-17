# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Option volume analytics (U.S. study Figures 1-7 equivalents) and the Top-30 / Rest split."""
import json

import numpy as np
import pandas as pd

import config as C
from src.analytics import common as cm

CR = 1e7  # Rs crore


def segment_series() -> pd.DataFrame:
    """Per weekly snapshot: contracts, premium, notional and OI notional for stock vs index options."""
    p = cm.panel(("date", "inst", "symbol", "opt", "contracts", "oi", "lot", "und", "premium", "und_notional", "dte"))
    p = p[(p["opt"] != "FUT") & p["date"].isin(cm.weekly_dates())].copy()
    p["oi_notional"] = p["oi"] * p["lot"] * p["und"]
    g = p.groupby(["date", "inst"], observed=True)[["contracts", "premium", "und_notional", "oi_notional"]].sum()
    seg = g.unstack("inst")
    seg.columns = [f"{a}_{'stk' if b == 'OPTSTK' else 'idx'}" for a, b in seg.columns]
    for s in ("stk", "idx"):
        seg[f"vol_oi_{s}"] = seg[f"und_notional_{s}"] / seg[f"oi_notional_{s}"]
    return seg


def dte_buckets() -> pd.DataFrame:
    p = cm.panel(("date", "inst", "opt", "und_notional", "dte"))
    p = p[(p["opt"] != "FUT") & p["date"].isin(cm.weekly_dates())]
    out = {}
    for inst, bins, labels in (
        ("OPTSTK", [-1, 7, 14, 30, 10_000], ["0-1W", "1-2W", "2-4W", ">4W"]),
        ("OPTIDX", [-1, 1, 7, 30, 10_000], ["0-1D", "2-7D", "1W-1M", ">1M"]),
    ):
        x = p[p["inst"] == inst].copy()
        x["bucket"] = pd.cut(x["dte"], bins, labels=labels)
        t = x.groupby(["date", "bucket"], observed=False)["und_notional"].sum().unstack() / CR
        t.columns = [str(c) for c in t.columns]
        out[inst] = t
    return out


def pcr() -> pd.DataFrame:
    a = cm.activity()
    a = a[a["date"].isin(cm.weekly_dates())]
    is_idx = a["symbol"].isin(C.INDEX_SYMBOLS)
    rows = {}
    for name, m in (("stk", ~is_idx), ("idx", is_idx)):
        s = a[m].groupby("date")[["contracts_ce", "contracts_pe", "oi_ce", "oi_pe"]].sum()
        rows[f"pcr_vol_{name}"] = s["contracts_pe"] / s["contracts_ce"]
        rows[f"pcr_oi_{name}"] = s["oi_pe"] / s["oi_ce"]
    return pd.DataFrame(rows)


def stock_notional_panel() -> pd.DataFrame:
    a = cm.activity()
    a = a[a["date"].isin(cm.weekly_dates()) & ~a["symbol"].isin(C.INDEX_SYMBOLS)].copy()
    a["notional"] = a["und_notional_ce"] + a["und_notional_pe"]
    return a.pivot_table(index="date", columns="symbol", values="notional", aggfunc="sum").fillna(0) / CR


def sector_breakdown(top_k: int = 6) -> pd.DataFrame:
    n = stock_notional_panel()
    sec = cm.sectors()
    lab = pd.Series({s: sec.get(s, "Other") for s in n.columns})
    by = n.T.groupby(lab).sum().T
    keep = by.sum().sort_values(ascending=False).index[:top_k]
    out = by[keep].copy()
    out["Other"] = by.drop(columns=keep).sum(axis=1)
    return out


def top_increase_table(n_show: int = 20) -> pd.DataFrame:
    n = stock_notional_panel()
    b0, b1 = C.BASELINE_PERIOD
    p0, p1 = C.PEAK_PERIOD
    base = n.loc[b0:b1].mean()
    peak = n.loc[p0:p1].mean()
    t = pd.DataFrame({"baseline": base, "peak": peak}).fillna(0)
    t["increase"] = t["peak"] - t["baseline"]
    t["multiple"] = t["peak"] / t["baseline"].replace(0, np.nan)
    t["sector"] = [cm.sectors().get(s, "n/a") for s in t.index]
    t = t.sort_values("increase", ascending=False)
    groups = {"top": list(t.index[:C.TOP_N]), "rest": list(t.index[C.TOP_N:])}
    (C.PROCESSED / "groups.json").write_text(json.dumps(groups, indent=1))
    return t.head(n_show)


def run() -> dict:
    seg = segment_series()
    seg.to_parquet(C.PROCESSED / "res_segments.parquet")
    dte = dte_buckets()
    dte["OPTSTK"].to_parquet(C.PROCESSED / "res_dte_stk.parquet")
    dte["OPTIDX"].to_parquet(C.PROCESSED / "res_dte_idx.parquet")
    pcr().to_parquet(C.PROCESSED / "res_pcr.parquet")
    sector_breakdown().to_parquet(C.PROCESSED / "res_sector.parquet")
    top = top_increase_table()
    top.to_csv(C.TABLES / "top20_volume_increase.csv")

    y = seg.groupby(seg.index.year).mean()
    stats = {
        "stk_notional_cr_2020": y.loc[2020, "und_notional_stk"] / CR,
        "stk_notional_cr_peak": seg.loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1], "und_notional_stk"].mean() / CR,
        "idx_notional_cr_2020": y.loc[2020, "und_notional_idx"] / CR,
        "idx_notional_cr_peak": seg.loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1], "und_notional_idx"].mean() / CR,
        "idx_premium_cr_2020": y.loc[2020, "premium_idx"] / CR,
        "idx_premium_cr_peak": seg.loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1], "premium_idx"].mean() / CR,
        "stk_premium_cr_2020": y.loc[2020, "premium_stk"] / CR,
        "stk_premium_cr_peak": seg.loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1], "premium_stk"].mean() / CR,
        "idx_notional_cr_last6m": seg["und_notional_idx"].iloc[-26:].mean() / CR,
        "stk_notional_cr_last6m": seg["und_notional_stk"].iloc[-26:].mean() / CR,
        "vol_oi_idx_2020": y.loc[2020, "vol_oi_idx"], "vol_oi_idx_peak": seg.loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1], "vol_oi_idx"].mean(),
        "vol_oi_stk_2020": y.loc[2020, "vol_oi_stk"], "vol_oi_stk_peak": seg.loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1], "vol_oi_stk"].mean(),
        "top_names": list(top.index[:10]),
    }
    d = dte["OPTIDX"]
    share = d.div(d.sum(axis=1), axis=0)
    stats["idx_share_le7d_2020"] = (share["0-1D"] + share["2-7D"]).loc["2020"].mean()
    stats["idx_share_le7d_peak"] = (share["0-1D"] + share["2-7D"]).loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1]].mean()
    ds = dte["OPTSTK"]
    sshare = ds.div(ds.sum(axis=1), axis=0)
    stats["stk_share_le2w_2020"] = (sshare["0-1W"] + sshare["1-2W"]).loc["2020"].mean()
    stats["stk_share_le2w_peak"] = (sshare["0-1W"] + sshare["1-2W"]).loc[C.PEAK_PERIOD[0]:C.PEAK_PERIOD[1]].mean()
    cm.save_result("volume", stats)
    return stats


if __name__ == "__main__":
    print(run())
