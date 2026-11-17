# Author: Siddhant Shukla <sidz0124@gmail.com>
"""VolScore short 1M delta-hedged ATM straddles on NSE single stocks (U.S. study trade idea #1).

Each monthly cycle (entry = first trading day after the stock-option expiry):
  VolScore = z(IV_atm - adjusted RV_3M) + z(IV_atm - sector median IV)
  Sell equal-notional ATM straddles on the VOLSCORE_N richest names, delta-hedge daily with
  futures at the entry IV, hold to expiry. Benchmarks: all eligible names, Top30 / Rest groups,
  and a NIFTY ATM delta-hedged straddle.
"""
from functools import lru_cache

import numpy as np
import pandas as pd

import config as C
from src.analytics import black76 as b76
from src.analytics import common as cm
from src.backtest import costs
from src.backtest.metrics import stats_table


def entry_chain(day: pd.DataFrame, symbol_filter=None) -> pd.DataFrame:
    """Front-month chain per symbol with forward, expiry and traded strikes only."""
    d = day["date"].iloc[0]
    opts = day[(day["opt"] != "FUT")]
    if symbol_filter is not None:
        opts = opts[opts["symbol"].isin(symbol_filter)]
    front = opts[opts["dte"] >= 14].groupby("symbol", observed=True)["expiry"].min().rename("front")
    opts = opts.join(front, on="symbol")
    opts = opts[opts["expiry"] == opts["front"]]
    fut = day[day["opt"] == "FUT"].set_index(["symbol", "expiry"])["settle"]
    key = pd.MultiIndex.from_frame(opts[["symbol", "expiry"]])
    opts = opts.assign(F=fut.reindex(key).values)
    carry = opts["und"] * np.exp(C.RISK_FREE * opts["dte"] / 365)
    opts["F"] = opts["F"].fillna(carry)
    opts["T"] = opts["dte"] / 365
    opts = opts[opts["contracts"] > 0]
    opts["symbol"] = opts["symbol"].astype(str)
    opts["opt"] = opts["opt"].astype(str)
    return opts.assign(date=d)


def atm_straddles(chain: pd.DataFrame) -> pd.DataFrame:
    piv = chain.pivot_table(index=["symbol", "strike"], columns="opt", values="close", aggfunc="first")
    if not {"CE", "PE"} <= set(piv.columns):
        return pd.DataFrame()
    piv = piv.dropna(subset=["CE", "PE"]).reset_index()
    meta = chain.groupby("symbol")[["F", "T", "und", "expiry", "lot"]].first()
    piv = piv.join(meta, on="symbol")
    piv["dist"] = (piv["strike"] / piv["F"] - 1).abs()
    best = piv.loc[piv.groupby("symbol")["dist"].idxmin()]
    best = best[best["dist"] < 0.03].copy()
    ivc = b76.implied_vol(best["CE"].values, best["F"].values, best["strike"].values, best["T"].values,
                          C.RISK_FREE, np.ones(len(best), bool))
    ivp = b76.implied_vol(best["PE"].values, best["F"].values, best["strike"].values, best["T"].values,
                          C.RISK_FREE, np.zeros(len(best), bool))
    best["iv"] = np.nanmean(np.vstack([ivc, ivp]), axis=0)
    best["premium"] = best["CE"] + best["PE"]
    return best.dropna(subset=["iv"]).set_index("symbol")


def price_path(symbol: str, d0, expiry, und0: float):
    """Daily closes from entry to expiry, rescaled to the bhavcopy underlying at entry."""
    close = cm.prices()[0]
    if symbol not in close.columns:
        return None
    s = close[symbol].loc[pd.Timestamp(d0) - pd.Timedelta(days=5):pd.Timestamp(expiry)].dropna()
    before = s.index[s.index <= pd.Timestamp(d0)]
    if len(before) == 0:
        return None
    s = s[s.index >= before.max()]
    if len(s) < 8 or s.index[-1] < pd.Timestamp(expiry) - pd.Timedelta(days=4):
        return None
    r = np.log(s).diff().abs()
    if (r > 0.25).any():
        return None
    return s * (und0 / s.iloc[0])


def short_dh_straddle_pnl(path: pd.Series, K: float, premium: float, iv: float, expiry,
                          d0, is_index: bool, slip_mult: float = 1.0) -> float:
    """P&L per unit of underlying, divided by entry spot."""
    S = path.values
    t = (pd.Timestamp(expiry) - path.index).days.values / 365
    t = np.maximum(t, 1e-6)
    dlt = 2 * b76.delta(S, K, t, iv, C.RISK_FREE, True) - 1  # straddle delta
    h = dlt[:-1]  # hedge held over each day (short straddle -> long delta hedge)
    hedge_pnl = np.sum(h * np.diff(S))
    payoff = abs(S[-1] - K)
    opt_pnl = premium - payoff
    # costs
    c = costs.option_trade_cost(premium, d0, sell=True, is_index=is_index, slip_mult=slip_mult)
    # bought back on expiry day close to intrinsic, where spreads are tighter
    c += costs.option_trade_cost(payoff, expiry, sell=False, is_index=is_index, slip_mult=slip_mult) * 0.67
    trades = np.diff(np.concatenate([[0.0], h, [0.0]]))
    px = np.concatenate([S[: len(h)], S[-1:]])
    bought = np.sum(np.clip(trades, 0, None) * px)
    sold = np.sum(np.clip(-trades, 0, None) * px)
    c += costs.futures_trade_cost(bought, sold, d0)
    return (opt_pnl + hedge_pnl - c) / S[0]


@lru_cache(None)
def _adj_rv() -> pd.DataFrame:
    return cm.adjusted_realized_vol(cm.prices()[0])


def volscore(straddles: pd.DataFrame, d) -> pd.DataFrame:
    rv = _adj_rv().loc[:pd.Timestamp(d)].iloc[-1]
    x = straddles.copy()
    x["adj_rv"] = rv.reindex(x.index)
    x["sector"] = [cm.sectors().get(s, "Other") for s in x.index]
    x["sector_med_iv"] = x.groupby("sector")["iv"].transform("median")
    x["spread_rv"] = x["iv"] - x["adj_rv"]
    x["spread_sec"] = x["iv"] - x["sector_med_iv"]

    def z(s):
        return ((s - s.mean()) / s.std()).clip(-3, 3)

    x["volscore"] = z(x["spread_rv"]) + z(x["spread_sec"])
    return x.dropna(subset=["volscore"])


def run() -> dict:
    p = cm.panel()
    groups = cm.groups()
    rows, scored_hist = [], []
    entries = [d for d in cm.entry_dates() if d >= pd.Timestamp("2020-02-01")]
    for d in entries:
        day = p[p["date"] == d]
        stk = day[day["inst"].isin(["OPTSTK", "FUTSTK"])]
        ch = entry_chain(stk)
        st = atm_straddles(ch)
        if len(st) < 30:
            continue
        sc = volscore(st, d)
        pnl, pnl2 = {}, {}
        for sym, r in sc.iterrows():
            path = price_path(sym, d, r["expiry"], r["und"])
            if path is None:
                continue
            pnl[sym] = short_dh_straddle_pnl(path, r["strike"], r["premium"], r["iv"], r["expiry"], d, False)
            pnl2[sym] = short_dh_straddle_pnl(path, r["strike"], r["premium"], r["iv"], r["expiry"], d, False, 2.0)
        sc["pnl"] = pd.Series(pnl)
        sc["pnl_2x"] = pd.Series(pnl2)
        sc = sc.dropna(subset=["pnl"])
        if len(sc) < 30:
            continue
        sc["date"] = d
        scored_hist.append(sc.reset_index())
        rich = sc.nlargest(C.VOLSCORE_N, "volscore")
        cheap = sc.nsmallest(C.VOLSCORE_N, "volscore")
        row = {
            "date": d,
            "VolScore Top20": rich["pnl"].mean(),
            "VolScore Top20 (2x slippage)": rich["pnl_2x"].mean(),
            "All stocks": sc["pnl"].mean(),
            "Top30 group": sc.loc[sc.index.isin(groups["top"]), "pnl"].mean(),
            "Rest group": sc.loc[~sc.index.isin(groups["top"]), "pnl"].mean(),
            "VolScore Bottom20": cheap["pnl"].mean(),
            "n_names": len(sc),
        }
        idx = day[day["symbol"] == "NIFTY"]
        ich = entry_chain(idx)
        if len(ich):
            stock_exp = rich["expiry"].iloc[0]
            exps = ich["expiry"].unique()
            best_exp = min(exps, key=lambda e: abs((pd.Timestamp(e) - pd.Timestamp(stock_exp)).days))
            ich = ich[ich["expiry"] == best_exp]
            ist = atm_straddles(ich)
            if "NIFTY" in ist.index:
                r = ist.loc["NIFTY"]
                path = price_path("NIFTY", d, r["expiry"], r["und"])
                if path is not None:
                    row["NIFTY DH straddle"] = short_dh_straddle_pnl(path, r["strike"], r["premium"], r["iv"],
                                                                     r["expiry"], d, True)
        rows.append(row)
        print(f"[straddle] {d.date()} names={len(sc)} rich={row['VolScore Top20']:.4f} all={row['All stocks']:.4f}")
    res = pd.DataFrame(rows).set_index("date")
    res.to_parquet(C.PROCESSED / "bt_straddle.parquet")
    hist = pd.concat(scored_hist, ignore_index=True)
    hist.to_parquet(C.PROCESSED / "bt_straddle_scores.parquet", index=False)
    cols = ["VolScore Top20", "VolScore Top20 (2x slippage)", "All stocks", "Top30 group", "Rest group", "VolScore Bottom20", "NIFTY DH straddle"]
    tab = stats_table(res[cols], 12)
    tab.to_csv(C.TABLES / "straddle_stats.csv")
    # current screen (latest entry date)
    last = hist[hist["date"] == hist["date"].max()].nlargest(10, "volscore")
    cm.save_result("straddle", {"stats": tab.round(4).to_dict(orient="index"),
                                "latest_rich": last[["symbol", "iv", "adj_rv", "sector_med_iv", "volscore"]]
                                .round(4).to_dict(orient="records")})
    return tab


if __name__ == "__main__":
    print(run().round(4).to_string())
