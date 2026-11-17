# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Implied-vol surface metrics per (date, underlying, expiry) and constant-maturity series.

Outputs
  surface_expiry.parquet : date, symbol, expiry, T, F, atm_iv, iv_p25, iv_c25, skew
  surface_cm.parquet     : date, symbol, iv30, iv60, skew30, term (iv30/iv60)
  activity.parquet       : date, symbol, call/put contracts & OI, option notional,
                           premium, delta-adjusted option volume (shares)
"""
import numpy as np
import pandas as pd

import config as C
from src.analytics import black76 as b76


def _forwards(day: pd.DataFrame) -> pd.Series:
    """Forward per (symbol, expiry): futures settle if listed, else put-call parity, else carry."""
    fut = day[day["opt"] == "FUT"].set_index(["symbol", "expiry"])["settle"]
    opts = day[(day["opt"] != "FUT") & (day["contracts"] > 0)]
    piv = opts.pivot_table(index=["symbol", "expiry", "strike"], columns="opt", values="close", aggfunc="first",
                           observed=True)
    fwd = {}
    if {"CE", "PE"} <= set(piv.columns):
        piv = piv.dropna(subset=["CE", "PE"]).reset_index()
        piv["diff"] = (piv["CE"] - piv["PE"]).abs()
        best = piv.loc[piv.groupby(["symbol", "expiry"], observed=True)["diff"].idxmin()]
        T = (best["expiry"] - day["date"].iloc[0]).dt.days.clip(lower=1) / 365
        best["F"] = best["strike"] + (best["CE"] - best["PE"]) * np.exp(C.RISK_FREE * T)
        fwd = best.set_index(["symbol", "expiry"])["F"]
    out = pd.Series(fwd, dtype=float)
    out = fut.combine_first(out) if len(fut) else out
    return out


def _interp_at(x, y, x0, max_gap=None):
    order = np.argsort(x)
    x, y = x[order], y[order]
    if len(x) < 2 or x0 < x[0] or x0 > x[-1]:
        return np.nan
    if max_gap is not None:
        i = np.searchsorted(x, x0)
        i = min(max(i, 1), len(x) - 1)
        if x[i] - x[i - 1] > max_gap:
            return np.nan
    return float(np.interp(x0, x, y))


def process_day(day: pd.DataFrame):
    d = day["date"].iloc[0]
    fwd = _forwards(day)
    opts = day[day["opt"] != "FUT"].copy()
    key = pd.MultiIndex.from_frame(opts[["symbol", "expiry"]].astype({"symbol": str}))
    fwd.index = pd.MultiIndex.from_arrays([fwd.index.get_level_values(0).astype(str), fwd.index.get_level_values(1)])
    opts["F"] = fwd.reindex(key).values
    carry_F = opts["und"] * np.exp(C.RISK_FREE * opts["dte"].clip(lower=1) / 365)
    opts["F"] = opts["F"].fillna(carry_F)
    opts["T"] = opts["dte"].clip(lower=1) / 365
    opts["is_call"] = opts["opt"] == "CE"
    opts["px"] = np.where(opts["contracts"] > 0, opts["close"], opts["settle"])
    opts["iv"] = b76.implied_vol(opts["px"].values, opts["F"].values, opts["strike"].values,
                                 opts["T"].values, C.RISK_FREE, opts["is_call"].values)

    # --- per-expiry smile metrics on OTM options -------------------------------------------
    otm = opts[((opts["is_call"] & (opts["strike"] >= opts["F"])) |
                (~opts["is_call"] & (opts["strike"] < opts["F"])))
               & opts["iv"].notna() & (opts["dte"] >= 3)
               & (opts["strike"] / opts["F"]).between(0.7, 1.3)].copy()
    otm["delta"] = b76.delta(otm["F"].values, otm["strike"].values, otm["T"].values, otm["iv"].values,
                             C.RISK_FREE, otm["is_call"].values)
    otm["lm"] = np.log(otm["strike"] / otm["F"])
    otm = otm.sort_values(["symbol", "expiry"])
    rows = []
    for (sym, exp), g in otm.groupby(["symbol", "expiry"], observed=True, sort=False):
        if len(g) < 3:
            continue
        lm, iv = g["lm"].values, g["iv"].values
        atm = _interp_at(lm, iv, 0.0, max_gap=0.12)
        puts, calls = g[~g["is_call"]], g[g["is_call"]]
        ivp = _interp_at(puts["delta"].values, puts["iv"].values, -0.25) if len(puts) >= 2 else np.nan
        ivc = _interp_at(calls["delta"].values, calls["iv"].values, 0.25) if len(calls) >= 2 else np.nan
        rows.append((d, str(sym), exp, g["T"].iloc[0], g["F"].iloc[0], atm, ivp, ivc, len(g)))
    surf = pd.DataFrame(rows, columns=["date", "symbol", "expiry", "T", "F", "atm_iv", "iv_p25", "iv_c25", "n"])
    surf["skew"] = (surf["iv_p25"] - surf["iv_c25"]) / surf["atm_iv"]

    # --- activity & delta-adjusted volume -----------------------------------------------
    atm_map = surf.set_index(["symbol", "expiry"])["atm_iv"]
    k2 = pd.MultiIndex.from_frame(opts[["symbol", "expiry"]].astype({"symbol": str}))
    sig = opts["iv"].fillna(pd.Series(atm_map.reindex(k2).values, index=opts.index))
    dl = b76.delta(opts["F"].values, opts["strike"].values, opts["T"].values, sig.fillna(0.3).values,
                   C.RISK_FREE, opts["is_call"].values)
    opts["dadj_sh"] = opts["contracts"] * opts["lot"] * np.abs(dl)
    g = opts.groupby(["symbol", "opt"], observed=True)
    act = pd.DataFrame({
        "contracts": g["contracts"].sum(), "oi": g["oi"].sum(), "premium": g["premium"].sum(),
        "und_notional": g["und_notional"].sum(), "dadj_sh": g["dadj_sh"].sum(),
    }).unstack("opt")
    act.columns = [f"{a}_{b.lower()}" for a, b in act.columns]
    act["und"] = opts.groupby("symbol", observed=True)["und"].median()
    act["date"] = d
    act = act.reset_index()
    act["symbol"] = act["symbol"].astype(str)
    return surf, act


def constant_maturity(surf: pd.DataFrame) -> pd.DataFrame:
    out = []
    surf = surf.dropna(subset=["atm_iv"]).sort_values(["date", "symbol", "T"])
    for (d, sym), g in surf.groupby(["date", "symbol"], sort=False):
        T, iv, sk = g["T"].values, g["atm_iv"].values, g["skew"].values
        tv = iv ** 2 * T

        def cm(target):
            if len(T) == 1:
                return iv[0] if abs(T[0] - target) < 20 / 365 else np.nan
            if target <= T[0]:
                return iv[0] if T[0] - target < 20 / 365 else np.nan
            if target >= T[-1]:
                return iv[-1] if target - T[-1] < 20 / 365 else np.nan
            return np.sqrt(np.interp(target, T, tv) / target)

        ok = ~np.isnan(sk)
        if ok.sum() >= 2 and T[ok][0] <= 30 / 365 <= T[ok][-1]:
            s30 = np.interp(30 / 365, T[ok], sk[ok])
        elif ok.any():
            j = np.argmin(np.abs(T[ok] - 30 / 365))
            s30 = sk[ok][j] if abs(T[ok][j] - 30 / 365) < 20 / 365 else np.nan
        else:
            s30 = np.nan
        out.append((d, sym, cm(30 / 365), cm(60 / 365), s30))
    cmdf = pd.DataFrame(out, columns=["date", "symbol", "iv30", "iv60", "skew30"])
    cmdf["term"] = cmdf["iv30"] / cmdf["iv60"]
    return cmdf


def run():
    panel = pd.read_parquet(C.PROCESSED / "fo_panel.parquet")
    keep = panel["inst"].isin(["OPTSTK", "FUTSTK"]) | panel["symbol"].isin(["NIFTY", "BANKNIFTY"])
    panel = panel[keep]
    surfs, acts = [], []
    for i, (d, day) in enumerate(panel.groupby("date")):
        s, a = process_day(day.reset_index(drop=True))
        surfs.append(s)
        acts.append(a)
        if i % 50 == 0:
            print(f"[surface] {i} {pd.Timestamp(d).date()} rows={len(s)}")
    surf = pd.concat(surfs, ignore_index=True)
    act = pd.concat(acts, ignore_index=True)
    surf.to_parquet(C.PROCESSED / "surface_expiry.parquet", index=False)
    act.to_parquet(C.PROCESSED / "activity.parquet", index=False)
    cm = constant_maturity(surf)
    cm.to_parquet(C.PROCESSED / "surface_cm.parquet", index=False)
    print(f"[surface] expiry rows {len(surf):,}; cm rows {len(cm):,}; "
          f"iv30 coverage {cm['iv30'].notna().mean():.0%}")


if __name__ == "__main__":
    run()
