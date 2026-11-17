# Author: Siddhant Shukla <sidz0124@gmail.com>
"""All report figures. Each function saves output/figures/figNN_*.png."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config as C  # noqa: E402
from src.backtest.metrics import nav  # noqa: E402

K = C.COLORS
P = C.PROCESSED
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
    "legend.frameon": False, "legend.fontsize": 8, "figure.dpi": 110, "savefig.dpi": 200,
})


def _ma(s, n=4):
    """Rolling median: robust to snapshots that land on index-expiry days."""
    return s.rolling(n, min_periods=1).median()


def _events(ax, keys=("2020-03-23", "2024-11-20")):
    for d in keys:
        ax.axvline(pd.Timestamp(d), color=K["grey"], ls="--", lw=0.8)
        ax.annotate(C.EVENTS[d], (pd.Timestamp(d), 1), xycoords=("data", "axes fraction"), fontsize=7,
                    color=K["grey"], rotation=90, va="top", ha="right")


def _fmt(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(C.FIGURES / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def fig_volume():
    seg = pd.read_parquet(P / "res_segments.parquet")
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.plot(_ma(seg["und_notional_stk"] / 1e12), color=K["navy"], lw=1.6, label="Stock options (LHS)")
    ax2 = ax.twinx()
    ax2.plot(_ma(seg["und_notional_idx"] / 1e12), color=K["teal"], lw=1.6, label="Index options (RHS)")
    ax.set_ylabel("Rs lakh crore / day"); ax2.set_ylabel("Rs lakh crore / day")
    ax2.grid(False); ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    ax.set_title("Daily option notional volume (contracts x lot x underlying, 4W median)")
    _events(ax); _fmt(ax)
    _save(fig, "fig01_notional")

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(_ma(seg["premium_stk"] / 1e7), color=K["navy"], lw=1.6, label="Stock options")
    ax.plot(_ma(seg["premium_idx"] / 1e7), color=K["teal"], lw=1.6, label="Index options")
    ax.set_ylabel("Rs crore / day"); ax.legend(); _fmt(ax); _events(ax)
    ax.set_title("Daily option premium turnover (4W rolling median)")
    _save(fig, "fig02_premium")

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(_ma(seg["vol_oi_stk"] * 100), color=K["navy"], label="Stock options (LHS)")
    ax2 = ax.twinx()
    ax2.plot(_ma(seg["vol_oi_idx"] * 100), color=K["teal"], label="Index options (RHS)")
    ax2.grid(False); ax2.spines["right"].set_visible(True)
    ax.set_ylabel("Volume / OI (%)"); ax2.set_ylabel("Volume / OI (%)")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left"); _fmt(ax); _events(ax)
    ax.set_title("Notional volume / open-interest notional (4W rolling median)")
    _save(fig, "fig03_vol_oi")


def fig_dte():
    di = pd.read_parquet(P / "res_dte_idx.parquet")
    ds = pd.read_parquet(P / "res_dte_stk.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    sh = di.div(di.sum(axis=1), axis=0).rolling(8, min_periods=1).mean() * 100
    axes[0].stackplot(sh.index, sh.T.values, labels=sh.columns,
                      colors=[K["navy"], K["teal"], K["orange"], K["grey"]], alpha=0.9)
    axes[0].set_title("Index options: notional share by DTE"); axes[0].set_ylim(0, 100)
    axes[0].legend(loc="lower left", ncol=2); axes[0].set_ylabel("%")
    sh = ds.div(ds.sum(axis=1), axis=0).rolling(8, min_periods=1).mean() * 100
    axes[1].stackplot(sh.index, sh.T.values, labels=sh.columns,
                      colors=[K["navy"], K["teal"], K["orange"], K["grey"]], alpha=0.9)
    axes[1].set_title("Stock options: notional share by DTE"); axes[1].set_ylim(0, 100)
    axes[1].legend(loc="lower left", ncol=2)
    for a in axes:
        a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig04_dte")


def fig_pcr():
    p = pd.read_parquet(P / "res_pcr.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9))
    for a, s, t in ((axes[0], "stk", "Stock options"), (axes[1], "idx", "Index options")):
        a.plot(_ma(p[f"pcr_vol_{s}"], 8), color=K["navy"], label="Volume PCR")
        a.plot(_ma(p[f"pcr_oi_{s}"], 8), color=K["orange"], label="OI PCR")
        a.set_title(f"{t}: put/call ratio (8W median)"); a.legend()
        a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig05_pcr")


def fig_sector():
    s = pd.read_parquet(P / "res_sector.parquet")
    s = s.rolling(8, min_periods=1).mean() / 1e5
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    cols = [K["navy"], K["teal"], K["orange"], K["green"], K["purple"], K["red"], K["grey"]]
    ax.stackplot(s.index, s.T.values, labels=s.columns, colors=cols[:s.shape[1]], alpha=0.9)
    ax.set_ylabel("Rs lakh crore / day"); ax.legend(loc="upper left", ncol=2, fontsize=7); _fmt(ax)
    ax.set_title("Stock option notional by sector (8W median)")
    _save(fig, "fig06_sector")


def fig_participants():
    p = pd.read_parquet(P / "res_participants.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    for who, c in (("Client", K["navy"]), ("Pro", K["teal"]), ("FII", K["orange"]), ("DII", K["grey"])):
        axes[0].plot(_ma(p[f"share_{who}_idx"] * 100, 8), color=c, label=who)
    axes[0].set_title("Share of index option volume (%)"); axes[0].legend(ncol=2)
    cl = p["total_contracts_idx"] * p["share_Client_idx"] / 1e6
    axes[1].bar(p.index, cl, width=6, color=K["navy"], alpha=0.8)
    axes[1].plot(_ma(cl, 8), color=K["orange"], lw=1.5, label="8W median")
    axes[1].set_title("Client index-option contracts (mn / day)"); axes[1].legend()
    for a in axes:
        a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
        a.axvline(pd.Timestamp(C.SEBI_CURB_DATE), color=K["grey"], ls="--", lw=0.8)
    _save(fig, "fig08_participants")

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    axes[0].plot(_ma(p["net_call_oi_Client_stk"] / 1e3, 4), color=K["navy"], label="Client")
    axes[0].plot(_ma(p["net_call_oi_FII_stk"] / 1e3, 4), color=K["orange"], label="FII")
    axes[0].plot(_ma(p["net_call_oi_Pro_stk"] / 1e3, 4), color=K["teal"], label="Pro")
    axes[0].axhline(0, color="k", lw=0.6)
    axes[0].set_title("Net long stock-call OI ('000 contracts)"); axes[0].legend()
    axes[1].plot(_ma(p["client_long_call_oi_share_stk"] * 100, 4), color=K["navy"], label="Stock calls")
    axes[1].plot(_ma(p["client_long_call_oi_share_idx"] * 100, 4), color=K["teal"], label="Index calls")
    axes[1].set_title("Client share of long call OI (%)"); axes[1].legend()
    for a in axes:
        a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig09_client_calls")


def fig_surface():
    a = pd.read_parquet(P / "res_surface_agg.parquet")
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(_ma(a["skew30_Top30"], 8), color=K["navy"], label="Top 30 (high option-volume growth)")
    ax.plot(_ma(a["skew30_Rest"], 8), color=K["orange"], label="Rest")
    ax.plot(_ma(a["skew30_NIFTY"], 8), color=K["grey"], ls=":", label="NIFTY")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_title("1M normalised 25-delta skew: (IV25P - IV25C) / ATM IV, 8W median"); ax.legend(); _fmt(ax); _events(ax)
    _save(fig, "fig10_skew")

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(_ma(a["term_Top30"], 8), color=K["navy"], label="Top 30")
    ax.plot(_ma(a["term_Rest"], 8), color=K["orange"], label="Rest")
    ax2 = ax.twinx()
    ax2.fill_between(a.index, 0, _ma(a["term_Top30"] - a["term_Rest"], 8), color=K["teal"], alpha=0.25,
                     label="Spread Top-Rest (RHS)")
    ax2.grid(False); ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right"); _fmt(ax)
    ax.set_title("Term structure: 30D / 60D ATM IV (8W median)")
    _save(fig, "fig11_term")

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    axes[0].plot(_ma(a["vrp_median_Top30"], 8), color=K["navy"], label="Top 30")
    axes[0].plot(_ma(a["vrp_median_Rest"], 8), color=K["orange"], label="Rest")
    axes[0].axhline(1, color="k", lw=0.6); axes[0].legend()
    axes[0].set_title("VRP: 1M IV / next-1M RV (median, 8W median)")
    ratio = _ma(a["vrp_median_Top30"] / a["vrp_median_Rest"], 8)
    axes[1].plot(ratio, color=K["purple"]); axes[1].axhline(1, color="k", lw=0.6)
    axes[1].set_title("Top 30 / Rest VRP ratio")
    for x in axes:
        x.xaxis.set_major_locator(mdates.YearLocator(2)); x.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig12_vrp")

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(a["iv30_NIFTY"] * 100, color=K["navy"], label="NIFTY 30D ATM IV (this study)")
    ax.plot(a["indiavix"] * 100, color=K["orange"], ls="--", lw=1, label="India VIX (NSE)")
    ax.plot(a["rv_fwd_NIFTY"] * 100, color=K["grey"], lw=0.8, label="Subsequent 1M realised vol")
    ax.set_ylabel("%"); ax.legend(); _fmt(ax)
    ax.set_title("Validation: bhavcopy-derived NIFTY IV vs India VIX")
    _save(fig, "fig13_nifty_iv")


def fig_hedging():
    h = pd.read_parquet(P / "res_hedging_flow.parquet")
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(_ma(h["opt_to_stock"]), color=K["navy"], label="Option notional / stock traded value (LHS)")
    ax2 = ax.twinx()
    ax2.plot(_ma(h["dadj_to_stock"]), color=K["orange"], label="Delta-adjusted option / stock traded value (RHS)")
    ax2.grid(False); ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left"); _fmt(ax); ax.set_ylabel("x"); ax2.set_ylabel("x")
    ax.set_title("Single-stock option vs cash-equity volume (4W rolling median)")
    _save(fig, "fig14_hedging")

    t = pd.read_csv(C.TABLES / "top10_delta_adj_ratio.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.bar(t.index, t["ratio"] * 100, color=K["navy"])
    ax.set_ylabel("%"); ax.tick_params(axis="x", rotation=30)
    ax.set_title("Top 10: delta-adjusted option volume as % of stock volume (last 4 weeks)")
    _save(fig, "fig15_top10_dadj")


def fig_eov():
    ra = pd.read_parquet(P / "res_eov_reg_all.parquet")
    rt = pd.read_parquet(P / "res_eov_reg_top.parquet")
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.0), sharex=True)
    for row, r, lab in ((0, ra, "All stocks"), (1, rt, "Top 50 growth")):
        axes[row, 0].bar(r.index, r["tstat"], width=6, color=K["teal"], alpha=0.5)
        axes[row, 0].plot(_ma(r["tstat"], 8), color=K["navy"])
        axes[row, 0].axhline(2, color=K["red"], ls=":", lw=0.8)
        axes[row, 0].set_title(f"{lab}: EOV t-stat (8W median)")
        axes[row, 1].plot(_ma(r["r2"] * 100, 8), color=K["navy"])
        axes[row, 1].set_title(f"{lab}: R-squared % (8W median)")
    for a in axes.flat:
        a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig16_eov_reg")

    q = pd.read_parquet(P / "res_eov_quintile.parquet")["spread"]
    rf = pd.read_parquet(P / "res_eov_reg_fwd.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9))
    axes[0].plot(nav(q, 100), color=K["red"])
    axes[0].set_title("Hi-minus-lo EOV quintile, next-week return (gross, =100)")
    axes[1].plot(_ma(rf["tstat"], 13), color=K["purple"]); axes[1].axhline(0, color="k", lw=0.6)
    axes[1].set_title("EOV vs next-5D return: t-stat (13W median)")
    for a in axes:
        a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig17_eov_reversal")


def fig_events():
    w = pd.read_parquet(P / "res_event_weekly.parquet")
    t = pd.read_csv(C.TABLES / "sebi_event_study.csv", index_col=0)
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    sub = w.loc["2023-06":]
    axes[0].plot(_ma(sub["Index option contracts (mn)"]), color=K["navy"], label="All participants")
    axes[0].plot(_ma(sub["Client contracts, index opt (mn)"]), color=K["orange"], label="Clients")
    axes[0].axvline(pd.Timestamp(C.SEBI_CURB_DATE), color=K["red"], ls="--", lw=1)
    axes[0].set_title("Index option contracts, mn/day (4W rolling median)"); axes[0].legend()
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%b-%y")); axes[0].tick_params(axis="x", rotation=30)
    m = ["Index option contracts (mn)", "Client contracts, index opt (mn)", "Index option premium (Rs cr)",
         "Index option notional (Rs lakh cr)", "Stock option notional (Rs '000 cr)"]
    lab = ["Idx contracts", "Client idx contracts", "Idx premium", "Idx notional", "Stk notional"]
    x = np.arange(len(m))
    axes[1].bar(x - 0.2, t.loc[m, "chg_post_pct"], 0.4, color=K["navy"], label="6M after vs 6M before")
    axes[1].bar(x + 0.2, t.loc[m, "chg_latest_pct"], 0.4, color=K["teal"], label="Latest 6M vs 6M before")
    axes[1].axhline(0, color="k", lw=0.6); axes[1].set_xticks(x); axes[1].set_xticklabels(lab, rotation=30, fontsize=7)
    axes[1].set_title("Change around SEBI curbs (%)"); axes[1].legend(fontsize=7)
    _save(fig, "fig18_sebi")


def fig_backtests():
    s = pd.read_parquet(P / "bt_straddle.parquet")
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for c, col, ls in (("VolScore Top20", K["navy"], "-"), ("VolScore Top20 (2x slippage)", K["navy"], ":"),
                       ("All stocks", K["teal"], "-"), ("VolScore Bottom20", K["grey"], "-"),
                       ("NIFTY DH straddle", K["orange"], "-")):
        ax.plot(nav(s[c]), color=col, ls=ls, label=c)
    ax.set_title("Short 1M delta-hedged ATM straddles, net of costs (NAV = 100)"); ax.legend(); _fmt(ax)
    _save(fig, "fig19_volscore")

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9))
    axes[0].plot(nav(s["Top30 group"]), color=K["navy"], label="Top 30 group")
    axes[0].plot(nav(s["Rest group"]), color=K["orange"], label="Rest")
    axes[0].set_title("Short DH straddles: Top 30 vs Rest"); axes[0].legend()
    yr = s[["VolScore Top20", "All stocks", "NIFTY DH straddle"]].groupby(s.index.year).sum() * 100
    yr.plot.bar(ax=axes[1], color=[K["navy"], K["teal"], K["orange"]], width=0.8)
    axes[1].set_title("Calendar-year return (%)"); axes[1].set_xlabel(""); axes[1].legend(fontsize=7)
    axes[1].tick_params(axis="x", rotation=0)
    axes[0].xaxis.set_major_locator(mdates.YearLocator(2)); axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig20_straddle_groups")

    c = pd.read_parquet(P / "bt_callspread.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9))
    axes[0].plot(nav(c["Screened call spreads"]), color=K["navy"], label="Screened (5% NAV premium/month)")
    axes[0].plot(nav(c["All-stock call spreads"]), color=K["grey"], label="All stocks")
    axes[0].set_title("ATM/+5% 1M call spreads, net of costs"); axes[0].legend(fontsize=7)
    tr = pd.read_csv(C.TABLES / "callspread_trades.csv")
    axes[1].hist(tr["ret"].clip(-1, 3), bins=30, color=K["teal"])
    axes[1].axvline(tr["ret"].mean(), color=K["red"], ls="--", lw=1)
    axes[1].set_title(f"Per-trade return distribution (mean {tr['ret'].mean():.1%})")
    axes[0].xaxis.set_major_locator(mdates.YearLocator(2)); axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%y"))
    _save(fig, "fig21_callspread")


def run():
    for f in (fig_volume, fig_dte, fig_pcr, fig_sector, fig_participants, fig_surface, fig_hedging, fig_eov,
              fig_events, fig_backtests):
        f()
    print(f"[figures] {len(list(C.FIGURES.glob('*.png')))} figures in {C.FIGURES}")


if __name__ == "__main__":
    run()
