# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Excess Option Volume factor and market-maker hedging flow (U.S. study Figs 24-29 analogue)."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

import config as C
from src.analytics import common as cm


def eov_panel() -> pd.DataFrame:
    a = cm.activity()
    a = a[a["date"].isin(cm.weekly_dates()) & ~a["symbol"].isin(C.INDEX_SYMBOLS)].copy()
    a = a.sort_values(["symbol", "date"])
    a["call_vol_oi"] = a["contracts_ce"] / a["oi_ce"].replace(0, np.nan)
    trail = a.groupby("symbol")["contracts_ce"].transform(lambda s: s.shift(1).rolling(4, min_periods=3).mean())
    a["call_vol_trail"] = a["contracts_ce"] / trail.replace(0, np.nan)
    for c in ("call_vol_oi", "call_vol_trail"):
        a[f"r_{c}"] = a.groupby("date")[c].rank(pct=True)
    a["eov"] = a[["r_call_vol_oi", "r_call_vol_trail"]].mean(axis=1, skipna=False)

    close, vol = cm.prices()
    r1 = close.pct_change(fill_method=None)
    fwd5 = close.shift(-5) / close - 1
    dates = pd.DatetimeIndex(sorted(a["date"].unique()))
    keys = pd.MultiIndex.from_frame(a[["date", "symbol"]])

    def lk(frame):
        st = frame.reindex(dates).stack(future_stack=True)
        st.index.names = ["date", "symbol"]
        return st.reindex(keys).values

    a["ret_1d"] = lk(r1)
    a["ret_fwd5"] = lk(fwd5)
    tv = close * vol
    a["stock_tv"] = lk(tv)
    a["opt_notional"] = a["und_notional_ce"] + a["und_notional_pe"]
    a["dadj_notional"] = (a["dadj_sh_ce"] + a["dadj_sh_pe"]) * a["und"]
    a.loc[a["ret_1d"].abs() > 0.25, "ret_1d"] = np.nan
    a.loc[a["ret_fwd5"].abs() > 0.4, "ret_fwd5"] = np.nan
    return a


def xs_regressions(a: pd.DataFrame, ret_col: str, universe=None) -> pd.DataFrame:
    rows = []
    for d, x in a.groupby("date"):
        if universe is not None:
            x = x[x["symbol"].isin(universe)]
        x = x.dropna(subset=["eov", ret_col])
        if len(x) < 15:
            continue
        y = x[ret_col].rank(pct=True)
        X = sm.add_constant(x["eov"].rank(pct=True))
        m = sm.OLS(y.values, X.values).fit()
        rows.append({"date": d, "tstat": m.tvalues[1], "beta": m.params[1], "r2": m.rsquared, "n": len(x)})
    return pd.DataFrame(rows).set_index("date")


def quintile_spread(a: pd.DataFrame) -> pd.Series:
    """Top-minus-bottom EOV quintile, equal-weight forward 5-day return (predictive test)."""
    out = {}
    for d, x in a.dropna(subset=["eov", "ret_fwd5"]).groupby("date"):
        if len(x) < 25:
            continue
        q = pd.qcut(x["eov"], 5, labels=False, duplicates="drop")
        out[d] = x.loc[q == q.max(), "ret_fwd5"].mean() - x.loc[q == 0, "ret_fwd5"].mean()
    return pd.Series(out).sort_index()


def hedging_flow(a: pd.DataFrame):
    agg = a.groupby("date")[["opt_notional", "dadj_notional", "stock_tv"]].sum()
    agg = agg[agg["stock_tv"] > 0]
    agg["opt_to_stock"] = agg["opt_notional"] / agg["stock_tv"]
    agg["dadj_to_stock"] = agg["dadj_notional"] / agg["stock_tv"]
    last = a[a["date"] >= a["date"].max() - pd.Timedelta(days=28)]
    per = last.groupby("symbol")[["dadj_notional", "stock_tv"]].sum()
    per = per[per["stock_tv"] > 0]
    per["ratio"] = per["dadj_notional"] / per["stock_tv"]
    top10 = per.sort_values("ratio", ascending=False).head(10)
    return agg, top10


def run() -> dict:
    a = eov_panel()
    a.to_parquet(C.PROCESSED / "res_eov_panel.parquet", index=False)
    g = cm.groups()
    reg_all = xs_regressions(a, "ret_1d")
    reg_top = xs_regressions(a, "ret_1d", g["top"] + g["rest"][:20])
    reg_fwd = xs_regressions(a, "ret_fwd5")
    for name, r in (("all", reg_all), ("top", reg_top), ("fwd", reg_fwd)):
        r.to_parquet(C.PROCESSED / f"res_eov_reg_{name}.parquet")
    qs = quintile_spread(a)
    qs.to_frame("spread").to_parquet(C.PROCESSED / "res_eov_quintile.parquet")
    agg, top10 = hedging_flow(a)
    agg.to_parquet(C.PROCESSED / "res_hedging_flow.parquet")
    top10.to_csv(C.TABLES / "top10_delta_adj_ratio.csv")

    peak = slice(*C.PEAK_PERIOD)

    def tstat_of_mean(x):
        x = x.dropna()
        return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))

    st = {
        "eov_t_mean_all": reg_all["tstat"].mean(), "eov_r2_mean_all": reg_all["r2"].mean(),
        "eov_t_mean_all_2020": reg_all.loc["2020", "tstat"].mean(),
        "eov_t_mean_all_peak": reg_all.loc[peak, "tstat"].mean(),
        "eov_r2_mean_all_peak": reg_all.loc[peak, "r2"].mean(),
        "eov_t_mean_all_last6m": reg_all["tstat"].iloc[-26:].mean(),
        "eov_frac_positive_t": float((reg_all["tstat"] > 0).mean()),
        "eov_fm_tstat_all": tstat_of_mean(reg_all["beta"]),
        "eov_t_mean_top": reg_top["tstat"].mean(), "eov_r2_mean_top": reg_top["r2"].mean(),
        "eov_t_mean_fwd": reg_fwd["tstat"].mean(), "eov_fm_tstat_fwd": tstat_of_mean(reg_fwd["beta"]),
        "eov_qspread_mean_wk": qs.mean(), "eov_qspread_tstat": tstat_of_mean(qs),
        "opt_to_stock_2020": agg.loc["2020", "opt_to_stock"].mean(),
        "opt_to_stock_peak": agg.loc[peak, "opt_to_stock"].mean(),
        "opt_to_stock_last6m": agg["opt_to_stock"].iloc[-26:].mean(),
        "dadj_to_stock_2020": agg.loc["2020", "dadj_to_stock"].mean(),
        "dadj_to_stock_peak": agg.loc[peak, "dadj_to_stock"].mean(),
        "dadj_to_stock_last6m": agg["dadj_to_stock"].iloc[-26:].mean(),
        "top10_dadj": list(top10.index),
    }
    cm.save_result("eov", st)
    return st


if __name__ == "__main__":
    print(run())
