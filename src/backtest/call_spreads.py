# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Long 1M ATM / +5% call spreads on flat-skew, fairly-priced, high-activity names (U.S. study idea #2).

Screen at each monthly entry date:
  - skew percentile vs the stock's own trailing 2Y weekly history (flatter = lower)
  - IV30 / adjusted RV_3M within a "fair" band
  - Excess Option Volume (EOV) rank from the latest weekly snapshot
Composite = (1 - skew_pct) + eov - |log(IV/RV)|; buy spreads on the top CALLSPREAD_N names.
"""
import numpy as np
import pandas as pd

import config as C
from src.analytics import common as cm
from src.backtest import costs
from src.backtest.metrics import stats_table
from src.backtest.straddle_volscore import _adj_rv, entry_chain, price_path


def skew_percentiles() -> pd.DataFrame:
    s = cm.surface_cm()
    wk = s[s["date"].isin(cm.weekly_dates())].pivot_table(index="date", columns="symbol", values="skew30")
    wk = wk.where(wk.abs() < 0.6)
    pct = wk.rolling(104, min_periods=26).apply(lambda x: (x[:-1] < x[-1]).mean() if np.isfinite(x[-1]) else np.nan,
                                                raw=True)
    return wk, pct


def screen(d, wk_skew, skew_pct, eov) -> pd.DataFrame:
    s = cm.surface_cm()
    cur = s[s["date"] == d].set_index("symbol")
    cur = cur[~cur.index.isin(C.INDEX_SYMBOLS)]
    adj = _adj_rv().loc[:d].iloc[-1]
    x = pd.DataFrame({"iv30": cur["iv30"], "skew30": cur["skew30"]})
    x["adj_rv"] = adj.reindex(x.index)
    x["iv_rv"] = x["iv30"] / x["adj_rv"]
    sp = skew_pct.loc[:d]
    x["skew_pct"] = sp.iloc[-1].reindex(x.index) if len(sp) else np.nan
    e = eov[eov["date"] <= d]
    e = e[e["date"] == e["date"].max()].set_index("symbol")["eov"] if len(e) else pd.Series(dtype=float)
    x["eov"] = e.reindex(x.index)
    x = x.dropna(subset=["iv30", "skew30", "adj_rv", "eov"])
    x["skew_pct"] = x["skew_pct"].fillna(x["skew30"].rank(pct=True))
    x["passes"] = (x["skew_pct"] <= 0.4) & x["iv_rv"].between(0.8, 1.4) & (x["eov"] >= 0.5)
    x["score"] = (1 - x["skew_pct"]) + x["eov"] - np.log(x["iv_rv"]).abs()
    return x.sort_values(["passes", "score"], ascending=False)


def spread_trade(chain: pd.DataFrame, sym: str, d, otm: float = C.CALLSPREAD_OTM):
    c = chain[(chain["symbol"] == sym) & (chain["opt"] == "CE")].sort_values("strike")
    if len(c) < 2:
        return None
    F = c["F"].iloc[0]
    k1 = c.iloc[(c["strike"] - F).abs().argmin()]
    upper = c[c["strike"] > k1["strike"]]
    if upper.empty:
        return None
    k2 = upper.iloc[(upper["strike"] - F * (1 + otm)).abs().argmin()]
    if k2["strike"] / F - 1 > otm * 2:
        return None
    debit = k1["close"] - k2["close"]
    if debit <= 0.002 * F:
        return None
    cost_in = (costs.option_trade_cost(k1["close"], d, sell=False, is_index=False)
               + costs.option_trade_cost(k2["close"], d, sell=True, is_index=False))
    return {"K1": k1["strike"], "K2": k2["strike"], "debit": debit, "cost_in": cost_in,
            "expiry": k1["expiry"], "und": k1["und"]}


def spread_return(tr: dict, sym: str, d):
    path = price_path(sym, d, tr["expiry"], tr["und"])
    if path is None:
        return None, None
    ST = path.iloc[-1]
    payoff = max(ST - tr["K1"], 0) - max(ST - tr["K2"], 0)
    cost_out = costs.option_trade_cost(payoff, tr["expiry"], sell=True, is_index=False) * 0.67
    ret = (payoff - cost_out) / (tr["debit"] + tr["cost_in"]) - 1
    stock_ret = ST / path.iloc[0] - 1
    return ret, stock_ret


def run() -> dict:
    p = cm.panel()
    wk_skew, skew_pct = skew_percentiles()
    eov = pd.read_parquet(C.PROCESSED / "res_eov_panel.parquet")[["date", "symbol", "eov"]]
    rows, trades = [], []
    for d in [d for d in cm.entry_dates() if d >= pd.Timestamp("2020-06-01")]:
        day = p[(p["date"] == d) & p["inst"].isin(["OPTSTK", "FUTSTK"])]
        chain = entry_chain(day)
        sc = screen(d, wk_skew, skew_pct, eov)
        res = {}
        for sym in sc.index:
            tr = spread_trade(chain, sym, d)
            if tr is None:
                continue
            r, sr = spread_return(tr, sym, d)
            if r is None:
                continue
            res[sym] = (r, sr)
        if len(res) < 20:
            continue
        rr = pd.DataFrame(res, index=["ret", "stock_ret"]).T
        sel = [s for s in sc.index if s in rr.index][:C.CALLSPREAD_N]
        n_pass = int(sc.loc[sel, "passes"].sum())
        for s in sel:
            trades.append({"date": d, "symbol": s, **sc.loc[s, ["skew30", "skew_pct", "iv_rv", "eov"]].to_dict(),
                           "ret": rr.loc[s, "ret"], "stock_ret": rr.loc[s, "stock_ret"]})
        rows.append({
            "date": d,
            "Screened call spreads": C.CALLSPREAD_BUDGET * rr.loc[sel, "ret"].mean(),
            "All-stock call spreads": C.CALLSPREAD_BUDGET * rr["ret"].mean(),
            "Screened avg spread return": rr.loc[sel, "ret"].mean(),
            "All avg spread return": rr["ret"].mean(),
            "Screened names, long stock": rr.loc[sel, "stock_ret"].mean(),
            "All names, long stock": rr["stock_ret"].mean(),
            "n_pass": n_pass,
        })
        print(f"[callspread] {d.date()} sel={len(sel)} pass={n_pass} spread={rr.loc[sel, 'ret'].mean():.3f}")
    res = pd.DataFrame(rows).set_index("date")
    res.to_parquet(C.PROCESSED / "bt_callspread.parquet")
    pd.DataFrame(trades).to_csv(C.TABLES / "callspread_trades.csv", index=False)
    tab = stats_table(res[["Screened call spreads", "All-stock call spreads",
                           "Screened names, long stock", "All names, long stock"]], 12)
    tab.loc["Screened call spreads", "Avg trade return"] = res["Screened avg spread return"].mean()
    tab.loc["All-stock call spreads", "Avg trade return"] = res["All avg spread return"].mean()
    tab.to_csv(C.TABLES / "callspread_stats.csv")

    # current recommendation table (latest weekly snapshot)
    last = cm.weekly_dates()[-1]
    cur = screen(last, wk_skew, skew_pct, eov)
    cur = cur[cur["passes"]].head(C.CALLSPREAD_N) if cur["passes"].sum() >= 5 else cur.head(C.CALLSPREAD_N)
    cur["sector"] = [cm.sectors().get(s, "n/a") for s in cur.index]
    cur.to_csv(C.TABLES / "callspread_current_screen.csv")
    cm.save_result("callspread", {"stats": tab.round(4).to_dict(orient="index"), "screen_date": str(last.date()),
                                  "current": list(cur.index)})
    return tab


if __name__ == "__main__":
    print(run().round(4).to_string())
