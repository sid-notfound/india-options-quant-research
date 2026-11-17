# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Research-style PDF note built from output/figures, output/tables and results.json."""
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

import config as C
from src.analytics.common import load_results

NAVY = colors.HexColor(C.COLORS["navy"])
TEAL = colors.HexColor(C.COLORS["teal"])
GREY = colors.HexColor("#555555")
LIGHT = colors.HexColor("#EAF3F8")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26,
                            textColor=NAVY, alignment=0, spaceAfter=6),
    "subtitle": ParagraphStyle("st", parent=ss["Normal"], fontName="Helvetica", fontSize=12, leading=15,
                               textColor=TEAL, spaceAfter=10),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17,
                         textColor=NAVY, spaceBefore=10, spaceAfter=6),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13,
                         textColor=NAVY, spaceBefore=8, spaceAfter=3),
    "body": ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12.5,
                           alignment=TA_JUSTIFY, spaceAfter=6),
    "bullet": ParagraphStyle("bl", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12.5,
                             leftIndent=12, bulletIndent=2, spaceAfter=4, alignment=TA_JUSTIFY),
    "figlab": ParagraphStyle("fl", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10,
                             textColor=TEAL, spaceBefore=6),
    "figtitle": ParagraphStyle("ft", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11,
                               textColor=NAVY, spaceAfter=2),
    "source": ParagraphStyle("src", parent=ss["Normal"], fontName="Helvetica-Oblique", fontSize=6.8, leading=8.5,
                             textColor=GREY, spaceAfter=8),
    "small": ParagraphStyle("sm", parent=ss["Normal"], fontName="Helvetica", fontSize=7, leading=9, textColor=GREY,
                            alignment=TA_JUSTIFY),
    "cell": ParagraphStyle("c", parent=ss["Normal"], fontName="Helvetica", fontSize=7, leading=8.5),
    "author": ParagraphStyle("au", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12.5, textColor=NAVY, spaceAfter=8),
    "box": ParagraphStyle("bx", parent=ss["Normal"], fontName="Helvetica", fontSize=8.6, leading=11.8,
                          alignment=TA_JUSTIFY, spaceAfter=4, leftIndent=10, bulletIndent=0),
}
SRC = "Source: NSE F&amp;O bhavcopies and participant-wise OI/volume (weekly samples), Yahoo Finance, own calculations."
_fig_no = [0]


def pct(x, d=0):
    return f"{x * 100:.{d}f}%"


def fx(x, d=1):
    return f"{x:,.{d}f}"


def figure(name, title, source=SRC, width=16.8 * cm):
    _fig_no[0] += 1
    p = C.FIGURES / f"{name}.png"
    img = Image(str(p))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = width, width * ratio
    return KeepTogether([Paragraph(f"FIGURE {_fig_no[0]}", S["figlab"]), Paragraph(title, S["figtitle"]), img,
                         Paragraph(source, S["source"])])


def table(df: pd.DataFrame, title: str, col_widths=None, source=SRC, font=7):
    _fig_no[0] += 1
    data = [[Paragraph(f"<b>{c}</b>", S["cell"]) for c in df.columns]]
    for _, r in df.iterrows():
        data.append([Paragraph(str(v), S["cell"]) for v in r.values])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, NAVY), ("FONTSIZE", (0, 0), (-1, -1), font),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return KeepTogether([Paragraph(f"FIGURE {_fig_no[0]}", S["figlab"]), Paragraph(title, S["figtitle"]), t,
                         Paragraph(source, S["source"])])


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items, style="bullet"):
    return [Paragraph(i, S[style], bulletText="\u25aa") for i in items]


def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 1.1 * cm, w, 1.1 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.6 * cm, h - 0.7 * cm, "India Equity Derivatives Strategy")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 1.6 * cm, h - 0.7 * cm, "Impact of Retail Options Trading")
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(1.6 * cm, 0.9 * cm, f"{C.AUTHOR_NAME}  |  {date.today().strftime('%d %B %Y')}  |  Quant research replication "
                                          f"of a U.S. study (Sep-2020) for NSE  |  For research purposes only")
    canvas.drawRightString(w - 1.6 * cm, 0.9 * cm, str(doc.page))
    canvas.restoreState()


def _cover(canvas, doc):
    _header_footer(canvas, doc)


def build():
    R = load_results()
    V, PT, SF, E, EV = R["volume"], R["participants"], R["surface"], R["eov"], R["events"]
    ST = R["straddle"]["stats"]
    CS = R["callspread"]["stats"]
    vs, allst, nifty = ST["VolScore Top20"], ST["All stocks"], ST["NIFTY DH straddle"]
    vs2 = ST["VolScore Top20 (2x slippage)"]
    top30, rest = ST["Top30 group"], ST["Rest group"]
    scs = CS["Screened call spreads"]
    ev = lambda m, k: EV[m][k]  # noqa: E731
    client_ct = pd.read_parquet(C.PROCESSED / "res_participants.parquet")
    client_ct = (client_ct["total_contracts_idx"] * client_ct["share_Client_idx"] / 1e6)
    cl20, cl24 = client_ct.loc["2020"].mean(), client_ct.loc["2024"].mean()

    doc = BaseDocTemplate(str(C.REPORT_PDF), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                          topMargin=1.7 * cm, bottomMargin=1.5 * cm,
                          title="India Equity Derivatives Strategy: Impact of Retail Options Trading",
                          author=C.AUTHOR_NAME)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate("cover", [frame], onPage=_cover),
                          PageTemplate("body", [frame], onPage=_header_footer)])
    st = []

    # ------------------------------------------------------------------ cover
    st += [Spacer(1, 0.3 * cm), P("India Equity Derivatives Strategy", "subtitle"),
           P("Impact of Retail Options Trading in India", "title"),
           P("A replication of a U.S. equity derivatives study (Sep-2020) on NSE data, Jan-2020 to "
             f"{pd.Timestamp(R['callspread']['screen_date']).strftime('%b-%Y')}", "subtitle")]
    st.append(P(
        f"<b>{C.AUTHOR_NAME}</b><br/>{C.AUTHOR_EDUCATION}<br/>{C.AUTHOR_DEGREE}<br/>"
        f"{C.AUTHOR_EMAIL}", "author"))
    st.append(P(
        "We replicate, for the Indian market, the framework used in a 2020 U.S. study to show that retail investors drove a "
        "surge in short-dated U.S. single-stock option volume, distorted the volatility surface and fed back into "
        "stock prices. India is the most extreme case of this phenomenon globally: NSE is the world's largest "
        "derivatives exchange by contracts traded, and SEBI's own studies show that roughly nine in ten individual "
        "F&amp;O traders lose money. We use weekly-sampled NSE bhavcopies (456 trading days, 7.4mn contract rows), "
        "NSE participant-wise data (Client / Pro / FII / DII) and daily prices for ~310 F&amp;O stocks."))
    st.append(P("Key findings", "h2"))
    st += bullets([
        f"<b>Volume explosion, concentrated in weekly index options.</b> Daily index-option notional rose "
        f"~{V['idx_notional_cr_peak'] / V['idx_notional_cr_2020']:.0f}x from 2020 to the pre-curb peak "
        f"(Rs {V['idx_notional_cr_2020'] / 1e5:.0f} to Rs {V['idx_notional_cr_peak'] / 1e5:.0f} lakh crore/day); "
        f"single-stock option notional rose {V['stk_notional_cr_peak'] / V['stk_notional_cr_2020']:.1f}x. "
        f"{pct(V['idx_share_le7d_peak'])} of index-option notional is in contracts expiring within 7 days.",
        f"<b>Retail fingerprints are direct, not inferred.</b> Unlike the U.S. (where retail flow had to be proxied "
        f"with small-lot trades), NSE reports client flow. Client index-option contracts rose from "
        f"{cl20:.0f}mn to {cl24:.0f}mn per day (2020 to 2024). Clients hold "
        f"{pct(PT['client_long_call_oi_share_stk_peak'])} of all long single-stock call OI and are structurally net "
        f"long calls, while FIIs are net short.",
        f"<b>Volatility surface.</b> Indian single-stock skew is structurally flat (about "
        f"{pct(SF['share_stocks_negative_skew'])} of stock-week observations have 25-delta call IV above put IV, vs "
        f"a steep NIFTY skew). VRP for the Top-30 'retail' names is consistently lower than for the rest "
        f"({SF['vrp_median_Top30_full']:.2f}x vs {SF['vrp_median_Rest_full']:.2f}x IV/RV), the same pattern as in the U.S. study "
        f"found. After SEBI's curbs, Top-30 skew steepened from {ev('Top30 skew', 'pre_6m'):.3f} to "
        f"{ev('Top30 skew', 'post_6m'):.3f} (p&lt;0.001), consistent with the removal of retail call demand.",
        f"<b>Option flow and stock returns.</b> The Excess Option Volume (EOV) factor explains same-day returns far "
        f"more strongly than in the U.S.: average weekly cross-sectional t-stat {E['eov_t_mean_all']:.1f}, positive in "
        f"{pct(E['eov_frac_positive_t'])} of weeks, R<super>2</super> {pct(E['eov_r2_mean_all'])}. "
        f"Delta-adjusted single-stock option volume is now ~{E['dadj_to_stock_last6m']:.1f}x cash-equity traded "
        f"value (vs ~0.4x in the 2020 U.S. study). Crucially, high-EOV stocks <i>underperform</i> the following week "
        f"(Fama-MacBeth t = {E['eov_fm_tstat_fwd']:.1f}): retail-driven price pressure partially reverses.",
        f"<b>SEBI curbs (20-Nov-2024) worked on contracts, not on notional.</b> Index-option contracts fell "
        f"{-ev('Index option contracts (mn)', 'chg_post_pct'):.0f}% and client contracts "
        f"{-ev('Client contracts, index opt (mn)', 'chg_post_pct'):.0f}% in the following six months, but notional "
        f"and premium turnover were broadly unchanged as lot sizes rose, and have since made new highs.",
        f"<b>Trade idea 1 works well: VolScore short delta-hedged straddles.</b> Selling 1M delta-hedged ATM "
        f"straddles on the 20 richest names by VolScore returned {pct(vs['CAGR'], 1)} CAGR (Sharpe "
        f"{vs['Sharpe']:.1f}, max drawdown {pct(vs['Max drawdown'], 1)}) net of STT, exchange fees and slippage, vs "
        f"{pct(allst['CAGR'], 1)} for all stocks and {pct(nifty['CAGR'], 1)} for the NIFTY straddle. With double "
        f"slippage the Sharpe is still {vs2['Sharpe']:.1f}.",
        f"<b>Trade idea 2 does not survive systematic testing in India.</b> Call spreads on flat-skew, high-activity "
        f"names returned {pct(scs['CAGR'], 1)} CAGR (avg trade {pct(scs['Avg trade return'], 1)}); the EOV reversal "
        f"explains why: chasing heavy retail call activity selects names that subsequently mean-revert.",
    ], "box")
    probe = Image(str(C.FIGURES / "fig01_notional.png"))
    w = 11.5 * cm
    cover_img = Image(str(C.FIGURES / "fig01_notional.png"), width=w, height=w * probe.imageHeight / probe.imageWidth)
    st += [Spacer(1, 0.15 * cm), cover_img, Paragraph(SRC, S["source"])]
    st.append(P("Prepared by Siddhant Shukla as an independent quant research replication. Not investment advice. "
                "Methodology, data limitations and disclaimer are on the final pages.", "small"))
    st += [NextPageTemplate("body"), PageBreak()]

    # ------------------------------------------------------------------ 1. volume
    st.append(P("1. A remarkable increase in Indian option volume", "h1"))
    st.append(P(
        "The starting point of the U.S. study was a 3x year-on-year rise in U.S. single-stock option volume. The Indian "
        "equivalent is larger and has a different shape. We measure option volume as the U.S. study did: contracts "
        "traded x lot size x underlying price (\"notional\"). Index options dominate: on an average sampled day at "
        f"the 2023-24 peak, index options traded Rs {V['idx_notional_cr_peak'] / 1e5:,.0f} lakh crore of notional "
        f"against Rs {V['stk_notional_cr_peak'] / 1e5:,.1f} lakh crore for single-stock options. Both grew "
        f"enormously from 2020 ({V['idx_notional_cr_peak'] / V['idx_notional_cr_2020']:.0f}x and "
        f"{V['stk_notional_cr_peak'] / V['stk_notional_cr_2020']:.1f}x respectively). Premium turnover, the cash "
        f"actually changing hands and a better gauge of retail spend, rose "
        f"{V['idx_premium_cr_peak'] / V['idx_premium_cr_2020']:.1f}x for index options and "
        f"{V['stk_premium_cr_peak'] / V['stk_premium_cr_2020']:.1f}x for stock options."))
    st.append(figure("fig01_notional", "Index-option notional rose more than 10x since 2020; single-stock option "
                                       "notional rose ~5x"))
    st.append(figure("fig02_premium", "Premium turnover - the money retail actually spends - grew ~5x in index "
                                      "options"))
    st.append(P("Volume is growing much faster than open interest", "h2"))
    st.append(P(
        "As in the U.S., the volume increase has not been matched by open interest. The ratio of daily index-option "
        f"notional to open-interest notional rose from {V['vol_oi_idx_2020']:.1f}x in 2020 to "
        f"{V['vol_oi_idx_peak']:.1f}x at the peak: index-option OI turns over many times a day, the signature of "
        "intraday speculation. For single-stock options the ratio is far lower and stable "
        f"({V['vol_oi_stk_2020']:.2f}x to {V['vol_oi_stk_peak']:.2f}x), because stock options only have monthly "
        "expiries."))
    st.append(figure("fig03_vol_oi", "Index-option volume turns over open interest ~12x a day"))
    st.append(P("The activity is overwhelmingly in the shortest-dated contracts", "h2"))
    st.append(P(
        "The U.S. study found the increase concentrated in options with less than two weeks to expiry. In India the "
        f"concentration is extreme: {pct(V['idx_share_le7d_peak'])} of index-option notional is in contracts with "
        f"seven days or less to expiry (vs {pct(V['idx_share_le7d_2020'])} in 2020). Weekly expiries on NIFTY, "
        "BANKNIFTY, FINNIFTY and MIDCPNIFTY meant there was an expiry almost every trading day until SEBI limited "
        "each exchange to one weekly benchmark expiry. Stock options, by contrast, show no structural shift in "
        f"tenor ({pct(V['stk_share_le2w_2020'])} vs {pct(V['stk_share_le2w_peak'])} within two weeks), since NSE "
        "lists only monthly stock options."))
    st.append(figure("fig04_dte", "More than 95% of index-option notional expires within a week"))
    st.append(P("Put/call ratios and sector mix", "h2"))
    st.append(P(
        "The U.S. study showed the single-stock put/call volume ratio falling to a five-year low as retail bought "
        "calls. Indian single-stock options have always been call-heavy: the volume PCR sits well below one. "
        "Index options are much closer to balanced because retail is active on both sides (buying cheap "
        "out-of-the-money options and, increasingly, selling them)."))
    st.append(figure("fig05_pcr", "Single-stock options are structurally call-heavy"))
    st.append(figure("fig06_sector", "Financials dominate single-stock option activity"))
    top = pd.read_csv(C.TABLES / "top20_volume_increase.csv", index_col=0)
    t = pd.DataFrame({
        "Rank": range(1, len(top) + 1), "Symbol": top.index,
        "Sector": [s[:26] for s in top["sector"]],
        "2020 (Rs cr/day)": [fx(v, 0) for v in top["baseline"]],
        "Peak (Rs cr/day)": [fx(v, 0) for v in top["peak"]],
        "Increase": [fx(v, 0) for v in top["increase"]],
        "Multiple": ["new" if pd.isna(m) else f"{m:.1f}x" for m in top["multiple"]],
    })
    st.append(P(
        "The table below lists the twenty stocks with the largest rise in option notional between 2020 and the "
        "Jan-2023 to Nov-2024 peak. The top 30 of this ranking form our <b>'Top 30'</b> basket (the analogue of "
        "the U.S. study's Top 100, scaled to India's ~200-name F&amp;O universe); all other F&amp;O stocks form the "
        "<b>'Rest'</b>. Like the U.S. study's list (TSLA, AMZN, AAPL...), it is dominated by large, liquid, retail-popular "
        "names: private and PSU banks, autos, IT, the Adani complex and defence (HAL)."))
    st.append(table(t, "Top 20 stocks by increase in average daily option notional (2020 vs Jan-23 to Nov-24)",
                    [1.1 * cm, 2.4 * cm, 4.4 * cm, 2.4 * cm, 2.4 * cm, 2.2 * cm, 1.8 * cm]))

    # ------------------------------------------------------------------ 2. retail
    st.append(PageBreak())
    st.append(P("2. The volume is being driven by retail investors", "h1"))
    st.append(P(
        "The U.S. study had no dataset that split U.S. option volume into retail and institutional flow, so it relied on "
        "circumstantial evidence: zero-commission brokerage, Robinhood holdings, 13F residuals and OCC small-lot "
        "trades. India is different: NSE publishes daily participant-wise volume and open interest for four "
        "categories: <b>Client</b> (retail and HNI individuals, corporates and other non-institutional accounts), "
        "<b>Pro</b> (brokers' proprietary books, including most HFT market makers), <b>FII</b> and <b>DII</b>."))
    st.append(P(
        "The Indian equivalents of the U.S. catalysts are well documented: discount brokers (Zerodha, Groww, Angel "
        "One, Upstox) with flat Rs 20 or zero brokerage, app-based eKYC onboarding, and the COVID lockdown. Demat "
        "accounts rose from about 4 crore in early 2020 to more than 19 crore by 2025 (NSDL/CDSL). SEBI's Jan-2023 "
        "study found 89% of individual F&amp;O traders lost money in FY22, and its Sep-2024 study found 93% lost "
        "money over FY22-FY24, with aggregate losses above Rs 1.8 lakh crore."))
    st.append(figure("fig08_participants", "Client index-option contracts rose ~9x into 2024; Pro (largely HFT "
                                           "market makers) took the other side"))
    st.append(P(
        f"Client index-option contracts rose from ~{cl20:.0f}mn per day in 2020 to ~{cl24:.0f}mn in 2024. The "
        f"<i>share</i> of client volume fell (from {pct(PT['share_Client_idx_2020'])} to "
        f"{pct(PT['share_Client_idx_peak'])}) only because proprietary volume grew even faster "
        f"({pct(PT['share_Pro_idx_2020'])} to {pct(PT['share_Pro_idx_peak'])}). That is what you would expect if "
        "market makers are intermediating a retail flow, and it matches the market-maker hedging channel the U.S. study "
        f"describes. FII share fell from {pct(PT['share_FII_idx_2020'])} to {pct(PT['share_FII_idx_peak'])}."))
    st.append(P("Retail is structurally long single-stock calls", "h2"))
    st.append(P(
        "The U.S. study's strongest retail evidence was that net call buying-to-open by retail had doubled while "
        "institutional demand stayed flat. Participant OI lets us observe positioning directly. Clients hold "
        f"{pct(PT['client_long_call_oi_share_stk_peak'])} of all long single-stock call open interest and "
        f"{pct(PT['client_long_call_oi_share_idx_peak'])} of long index-call OI. In single-stock options clients "
        f"are net long calls (average {PT['client_net_call_oi_stk_peak'] / 1e3:,.0f}k contracts at the peak) while "
        f"FIIs are net short ({PT['fii_net_call_oi_stk_peak'] / 1e3:,.0f}k). Intraday client buy/sell volume is "
        f"close to balanced (call buy/sell ratio {PT['client_call_bs_stk_peak']:.2f}), confirming that most of the "
        "volume is round-trip day trading layered on top of a persistent long-call position."))
    st.append(figure("fig09_client_calls", "Clients are net long single-stock calls and own most long-call OI"))

    # ------------------------------------------------------------------ 3. surface
    st.append(PageBreak())
    st.append(P("3. Impact on the volatility surface", "h1"))
    st.append(P(
        "We back out Black-76 implied volatilities for every traded (or open-interest-bearing) option in each "
        "sampled bhavcopy, using the matching futures settlement price as the forward (put-call parity where no "
        "future is listed) and a 6.5% rate. For each underlying and expiry we interpolate ATM and 25-delta "
        "implied vols, then build constant-maturity 30-day and 60-day measures. Group aggregates are weighted by "
        "trailing 3-month traded value (a market-cap proxy), as the U.S. study used market-cap weights. As a check on "
        "the pipeline, our NIFTY 30-day ATM IV tracks NSE's India VIX very closely (Figure 13)."))
    st.append(figure("fig13_nifty_iv", "Validation: bhavcopy-derived NIFTY 30D ATM IV vs India VIX"))
    st.append(P("Skew: structurally flat for single stocks, and it steepened when SEBI curbed retail", "h2"))
    st.append(P(
        "The U.S. study found that the skew of high-activity names flattened sharply as retail bought upside calls. "
        "In India, single-stock skew is flat to inverted most of the time: the normalised 25-delta skew "
        f"(put minus call IV over ATM) averages {SF['skew30_Top30_full']:.3f} for the Top 30 and "
        f"{SF['skew30_Rest_full']:.3f} for the Rest, against {SF['skew30_NIFTY_full']:.3f} for NIFTY. Roughly "
        f"{pct(SF['share_stocks_negative_skew'])} of stock-week observations show call IV above put IV. The most "
        "telling evidence is the natural experiment: in the six months after SEBI's Nov-2024 curbs, Top-30 skew "
        f"steepened from {ev('Top30 skew', 'pre_6m'):.3f} to {ev('Top30 skew', 'post_6m'):.3f} "
        f"(p = {ev('Top30 skew', 'p_value'):.4f}), and NIFTY skew from {ev('NIFTY 30D skew', 'pre_6m'):.3f} to "
        f"{ev('NIFTY 30D skew', 'post_6m'):.3f}. Removing some retail upside demand made the surface look more like "
        "a 'normal' equity surface."))
    st.append(figure("fig10_skew", "Single-stock skew is flat; it steepened after the SEBI curbs"))
    st.append(P("Term structure", "h2"))
    st.append(P(
        "The U.S. study measured term structure as 1M/3M IV; Indian stock options list only three monthly expiries and "
        "the third is often illiquid, so we use 30D/60D. Unlike in the U.S., we find no persistent inversion of "
        f"the Top-30 term structure relative to the Rest (peak-period averages {SF['term_Top30_peak']:.3f} vs "
        f"{SF['term_Rest_peak']:.3f}). Retail short-dated demand in India is expressed mainly through weekly "
        "<i>index</i> options, so it shows up less in the single-stock term structure."))
    st.append(figure("fig11_term", "Single-stock 30D/60D term structure: no persistent Top-30 distortion"))
    st.append(P("VRP: muted for the retail-heavy names, just as the U.S. study found", "h2"))
    st.append(P(
        "Despite heavy option demand, the volatility risk premium (30D IV divided by subsequent 21-day realised "
        f"vol) is consistently <i>lower</i> for the Top 30 ({SF['vrp_median_Top30_full']:.2f}x on average) than "
        f"for the Rest ({SF['vrp_median_Rest_full']:.2f}x). During the 2023-24 peak the gap widened to "
        f"{SF['vrp_median_Top30_peak']:.2f}x vs {SF['vrp_median_Rest_peak']:.2f}x. As the U.S. study argued, this means "
        "realised volatility rose along with implied: speculative flow and market makers' gamma hedging make "
        "the stocks themselves more volatile, so buyers of options on these names are not obviously overpaying. "
        "VRP has compressed across the board since 2024."))
    st.append(figure("fig12_vrp", "Top-30 VRP is persistently below the Rest"))

    # ------------------------------------------------------------------ 4. stock prices
    st.append(PageBreak())
    st.append(P("4. Option activity is large enough to move stock prices", "h1"))
    st.append(P(
        "When a client buys a call, a market maker sells it and buys delta in the underlying. The U.S. study showed "
        "delta-adjusted U.S. single-stock option volume reaching ~40% of stock volume. In India the ratio is an "
        f"order of magnitude higher: single-stock option notional went from {E['opt_to_stock_2020']:.1f}x to "
        f"{E['opt_to_stock_peak']:.1f}x of cash-equity traded value, and <b>delta-adjusted</b> option volume from "
        f"{E['dadj_to_stock_2020']:.2f}x to {E['dadj_to_stock_peak']:.2f}x (last six months: "
        f"{E['dadj_to_stock_last6m']:.2f}x). Not all of this is hedged in cash (two-way flow nets out, and futures "
        "are a cheaper hedge), but the potential feedback channel is far larger than in the U.S."))
    st.append(figure("fig14_hedging", "Delta-adjusted stock-option volume is now ~3x cash-equity volume"))
    st.append(figure("fig15_top10_dadj", "Names where option hedging flow is largest relative to the stock"))
    st.append(P("Excess Option Volume (EOV) explains the cross-section of returns", "h2"))
    st.append(P(
        "We follow the U.S. study's definition: EOV is the average of the cross-sectional percentile ranks of (i) call volume "
        "/ call open interest and (ii) call volume / its trailing average (four weekly snapshots, about one month). Each "
        "week we regress the cross-sectional rank of same-day stock returns on EOV rank. The relationship is "
        f"strong and persistent: the average t-stat is {E['eov_t_mean_all']:.1f}, positive in "
        f"{pct(E['eov_frac_positive_t'])} of weeks (Fama-MacBeth t = {E['eov_fm_tstat_all']:.0f}), with an "
        f"average R<super>2</super> of {pct(E['eov_r2_mean_all'])}, several times the 1-5% reported in the U.S. study. "
        f"Within the Top-50 growth names the R<super>2</super> is higher still ({pct(E['eov_r2_mean_top'])}). "
        "Same-day correlation is not causation: big up-moves attract call buying too. But the stability of the "
        "relationship is consistent with option flow acting as a return 'factor'."))
    st.append(figure("fig16_eov_reg", "Weekly cross-sectional regressions of same-day returns on EOV"))
    st.append(P("...and the pressure partially reverses", "h2"))
    st.append(P(
        "We extend the U.S. study with a predictive test. Regressing <i>next-five-day</i> returns on EOV "
        f"gives a negative Fama-MacBeth t-stat of {E['eov_fm_tstat_fwd']:.1f}, and a weekly high-minus-low EOV "
        f"quintile portfolio loses {E['eov_qspread_mean_wk'] * 100:.2f}% per week on average (t = "
        f"{E['eov_qspread_tstat']:.1f}, gross of costs). Stocks that see a burst of retail call activity tend to "
        "give back part of the move. This is the hallmark of non-fundamental price pressure, and it matters for "
        "trade construction (Section 6). After realistic round-trip cash-equity costs of ~0.2-0.3%, the reversal "
        "is not a standalone strategy, but it is a useful timing and filtering signal."))
    st.append(figure("fig17_eov_reversal", "High-EOV stocks underperform the following week"))

    # ------------------------------------------------------------------ 5. SEBI
    st.append(PageBreak())
    st.append(P("5. A natural experiment: SEBI's F&amp;O curbs", "h1"))
    st.append(P(
        "On 1-Oct-2024 SEBI announced measures to curb retail index-derivative speculation, effective from "
        "20-Nov-2024: one weekly benchmark expiry per exchange, a minimum contract size of Rs 15 lakh (roughly tripling "
        "lot sizes), extra margin on expiry day, upfront premium collection and (later) intraday position-limit "
        "monitoring. The STT on options had already risen from 0.0625% to 0.1% of premium on 1-Oct-2024. The "
        "U.S. study had no comparable experiment, so we compare six months before with six months after, and with "
        "the latest six months."))
    t = pd.read_csv(C.TABLES / "sebi_event_study.csv", index_col=0)
    level = {"Client share, index options", "Client share, stock options", "0-1D share of index notional",
             "NIFTY 30D ATM IV", "NIFTY 30D skew", "Top30 skew", "Top30 VRP (IV/RV)", "Rest VRP (IV/RV)"}
    rows = []
    for m, r in t.iterrows():
        if m in level:
            fmtv = (lambda v: f"{v:.3f}")
            rows.append([m, fmtv(r.pre_6m), fmtv(r.post_6m), fmtv(r.latest_6m),
                         f"{r.post_6m - r.pre_6m:+.3f}", f"{r.latest_6m - r.pre_6m:+.3f}", f"{r.p_value:.3f}"])
        else:
            rows.append([m, fx(r.pre_6m), fx(r.post_6m), fx(r.latest_6m), f"{r.chg_post_pct:+.0f}%",
                         f"{r.chg_latest_pct:+.0f}%", f"{r.p_value:.3f}"])
    tdf = pd.DataFrame(rows, columns=["Metric (weekly-snapshot average)", "6M pre", "6M post", "Latest 6M",
                                      "Post vs pre", "Latest vs pre", "p (Welch)"])
    st.append(table(tdf, "SEBI curbs event study (pre: 20-May to 19-Nov-2024; post: 20-Nov-2024 to 19-May-2025)",
                    [5.6 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.9 * cm, 1.6 * cm]))
    st.append(P(
        f"The curbs cut index-option <b>contracts</b> by {-ev('Index option contracts (mn)', 'chg_post_pct'):.0f}% "
        f"and client contracts by {-ev('Client contracts, index opt (mn)', 'chg_post_pct'):.0f}% (both p&lt;0.01). "
        f"But because each contract became ~3x larger, notional ({ev('Index option notional (Rs lakh cr)', 'chg_post_pct'):+.0f}%) "
        f"and premium ({ev('Index option premium (Rs cr)', 'chg_post_pct'):+.0f}%) barely moved, and both are now "
        f"above pre-curb levels ({ev('Index option notional (Rs lakh cr)', 'chg_latest_pct'):+.0f}% and "
        f"{ev('Index option premium (Rs cr)', 'chg_latest_pct'):+.0f}%). The measures removed the smallest "
        "tickets and the clients who traded them, not the activity itself. The client share of stock-option "
        f"volume fell from {pct(ev('Client share, stock options', 'pre_6m'))} to "
        f"{pct(ev('Client share, stock options', 'post_6m'))}, and the steepening of single-stock skew noted in "
        "Section 3 is the clearest surface-level effect."))
    st.append(figure("fig18_sebi", "Contracts fell ~45%, notional did not"))

    # ------------------------------------------------------------------ 6. trades
    st.append(PageBreak())
    st.append(P("6. Monetising the retail-driven dislocation", "h1"))
    st.append(P("Trade idea 1: selective short single-stock volatility with VolScore", "h2"))
    st.append(P(
        "Following the VolScore approach of the U.S. study, on the first trading day after each monthly expiry we score every "
        "stock with a liquid ATM straddle by the sum of two cross-sectional z-scores: (i) ATM IV minus "
        "<i>outlier-adjusted</i> 3-month realised vol (daily returns clipped at the median +/- 3 robust standard "
        "deviations, so that single jumps do not dominate) and (ii) ATM IV minus the sector-median IV. We sell "
        "equal-notional 1M ATM straddles on the 20 richest names, delta-hedge daily at the entry IV and hold to "
        "expiry. Costs include STT (0.0625% then 0.1% of premium sold, 0.0125%/0.02% on futures sold), exchange "
        "fees plus GST, stamp duty, and slippage of 1.5% of premium per stock-option leg (0.5% for NIFTY) and 1bp on "
        "hedge trades. Strategy notional equals 100% of NAV."))
    s = pd.read_csv(C.TABLES / "straddle_stats.csv", index_col=0)
    sdf = pd.DataFrame({
        "Strategy": s.index, "CAGR": [pct(v, 1) for v in s["CAGR"]], "Ann. vol": [pct(v, 1) for v in s["Ann. vol"]],
        "Sharpe": [f"{v:.2f}" for v in s["Sharpe"]], "Max DD": [pct(v, 1) for v in s["Max drawdown"]],
        "Hit rate": [pct(v) for v in s["Hit rate"]], "Worst month": [pct(v, 1) for v in s["Worst period"]],
        "Cycles": [f"{v:.0f}" for v in s["Periods"]]})
    st.append(figure("fig19_volscore", "VolScore-selected short delta-hedged straddles beat both the all-stock "
                                       "and NIFTY versions"))
    st.append(table(sdf, "Short 1M delta-hedged straddle backtests, net of costs (monthly cycles, Feb-2020 onward)",
                    [5.2 * cm, 1.6 * cm, 1.6 * cm, 1.4 * cm, 1.6 * cm, 1.6 * cm, 2.0 * cm, 1.4 * cm]))
    st.append(P(
        f"The VolScore portfolio returned {pct(vs['CAGR'], 1)} a year with {pct(vs['Ann. vol'], 1)} volatility "
        f"(Sharpe {vs['Sharpe']:.2f}) and won in {pct(vs['Hit rate'])} of cycles. The ranking is monotonic: "
        f"the 20 cheapest names by VolScore earned only {pct(ST['VolScore Bottom20']['CAGR'], 1)}. Consistent with "
        f"Section 3, selling volatility on the retail-heavy Top 30 earned less ({pct(top30['CAGR'], 1)}) than on "
        f"the Rest ({pct(rest['CAGR'], 1)}), because their realised volatility rose with their implied. The "
        f"single-stock VolScore approach beats the NIFTY delta-hedged straddle ({pct(nifty['CAGR'], 1)}) by a "
        "wide margin, replicating the U.S. study's finding that selective single-stock volatility selling outperforms "
        "the index version. Two caveats: returns have decayed as VRP compressed after 2023, and the result is "
        f"sensitive to execution (with 2x slippage, CAGR {pct(vs2['CAGR'], 1)}, Sharpe {vs2['Sharpe']:.2f})."))
    st.append(figure("fig20_straddle_groups", "Retail-heavy names offer less VRP; annual returns have decayed with "
                                              "VRP compression"))
    rich = pd.DataFrame(R["straddle"]["latest_rich"])
    rich = pd.DataFrame({"Symbol": rich["symbol"], "ATM IV": [pct(v, 1) for v in rich["iv"]],
                         "Adj. RV 3M": [pct(v, 1) for v in rich["adj_rv"]],
                         "Sector median IV": [pct(v, 1) for v in rich["sector_med_iv"]],
                         "VolScore": [f"{v:.2f}" for v in rich["volscore"]]})
    st.append(table(rich, "Current VolScore screen: richest 10 single-stock straddles at the latest monthly entry",
                    [3.0 * cm, 2.4 * cm, 2.4 * cm, 3.0 * cm, 2.4 * cm]))

    st.append(P("Trade idea 2: long call spreads on flat-skew, high-activity names", "h2"))
    st.append(P(
        "The U.S. study's second idea was to express bullish views on the high-activity 'resilient' names through call "
        "spreads, selling the flat (cheap) upside skew. We test a systematic version: each month we screen for "
        "skew in the bottom 40% of its own two-year history, IV/adjusted-RV between 0.8 and 1.4 (fair vol), and "
        "EOV rank at or above 0.5 (elevated activity), then buy ATM / +5% 1M call spreads on the ten best-scoring "
        f"names, spending {pct(C.CALLSPREAD_BUDGET)} of NAV in premium per month."))
    c = pd.read_csv(C.TABLES / "callspread_stats.csv", index_col=0)
    cdf = pd.DataFrame({
        "Strategy": c.index, "CAGR": [pct(v, 1) for v in c["CAGR"]], "Ann. vol": [pct(v, 1) for v in c["Ann. vol"]],
        "Sharpe": [f"{v:.2f}" for v in c["Sharpe"]], "Max DD": [pct(v, 1) for v in c["Max drawdown"]],
        "Hit rate": [pct(v) for v in c["Hit rate"]],
        "Avg trade": ["" if pd.isna(v) else pct(v, 1) for v in c["Avg trade return"]]})
    st.append(figure("fig21_callspread", "Systematic call spreads on the screen roughly break even"))
    st.append(table(cdf, "Call-spread backtest vs simply owning the same names (monthly, Jun-2020 onward)",
                    [5.4 * cm, 1.8 * cm, 1.8 * cm, 1.6 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm]))
    st.append(P(
        f"The result is negative: screened spreads returned {pct(scs['CAGR'], 1)} CAGR, with an average trade "
        f"return of {pct(scs['Avg trade return'], 1)}, no better than buying spreads on every stock. Owning the "
        "names outright did better over a period in which Indian equities rallied. The EOV reversal in Section 4 "
        "explains much of this: requiring elevated call activity selects stocks whose recent moves are partly "
        "retail price pressure that subsequently fades. A discretionary overlay (the U.S. study paired the screen with a "
        "fundamental 'resilient' thesis) may still add value, but we find no systematic edge."))
    cur = pd.read_csv(C.TABLES / "callspread_current_screen.csv", index_col=0)
    cdf2 = pd.DataFrame({"Symbol": cur.index, "Sector": [s[:24] for s in cur["sector"]],
                         "Skew 30D": [f"{v:.3f}" for v in cur["skew30"]],
                         "Skew pctile (2Y)": [pct(v) for v in cur["skew_pct"]],
                         "IV 30D": [pct(v, 1) for v in cur["iv30"]], "Adj. RV": [pct(v, 1) for v in cur["adj_rv"]],
                         "IV/RV": [f"{v:.2f}" for v in cur["iv_rv"]], "EOV": [f"{v:.2f}" for v in cur["eov"]]})
    st.append(table(cdf2, f"Current flat-skew / fair-vol / high-activity screen ({R['callspread']['screen_date']}) "
                          "- shown for completeness, given the weak backtest",
                    [2.4 * cm, 3.8 * cm, 1.6 * cm, 2.2 * cm, 1.6 * cm, 1.6 * cm, 1.4 * cm, 1.4 * cm]))

    # ------------------------------------------------------------------ 7. conclusions & methodology
    st.append(PageBreak())
    st.append(P("7. Conclusions: how India compares with the U.S. study", "h1"))
    comp = pd.DataFrame([
        ["Volume surge", "Single-stock options ~3x YoY, short-dated calls",
         f"Index options ~{V['idx_notional_cr_peak'] / V['idx_notional_cr_2020']:.0f}x, stock options "
         f"~{V['stk_notional_cr_peak'] / V['stk_notional_cr_2020']:.0f}x; >95% of index notional within 7 days"],
        ["Retail evidence", "Indirect (small lots, 13F, brokers)",
         "Direct (NSE client data); clients own ~3/4 of long stock-call OI"],
        ["Skew", "Flattened for Top 100", "Structurally flat; steepened after SEBI curbs"],
        ["Term structure", "Inverted for Top 100", "No persistent single-stock effect (retail is in index weeklies)"],
        ["VRP", "Lower for Top 100", "Lower for Top 30 (confirmed)"],
        ["Hedging flow / stock volume", "~40%", f"~{E['dadj_to_stock_last6m'] * 100:.0f}%"],
        ["EOV vs same-day returns", "t-stat rising, R2 1-5%",
         f"t ~{E['eov_t_mean_all']:.1f}, R2 ~{E['eov_r2_mean_all'] * 100:.0f}%; reverses next week"],
        ["Short-vol (VolScore)", "Outperformed SPX benchmark", f"Sharpe {vs['Sharpe']:.1f} vs NIFTY {nifty['Sharpe']:.1f}"],
        ["Call spreads", "Recommended", "No systematic edge"],
    ], columns=["Dimension", "U.S. (2020 study)", "India (this study)"])
    st.append(table(comp, "Summary comparison", [3.6 * cm, 5.6 * cm, 8.0 * cm], source="Source: U.S. equity derivatives research note "
                                                                                     "(Sep-2020); this study."))
    st.append(P(
        "The U.S. episode described in 2020 has played out in India at a far larger scale, and for longer. "
        "The evidence is more direct here because NSE identifies client flow. The core mechanisms carry over: "
        "retail demand for cheap, short-dated calls; market makers intermediating and hedging; muted VRP on the "
        "names retail favours, because realised volatility rises too; and option flow strong enough to show up in "
        "the cross-section of stock returns. The main differences come from market structure: retail activity is "
        "concentrated in weekly index options, single-stock skew is structurally flat, and the price pressure from "
        "call buying is partly temporary. For volatility sellers the opportunity is real but has narrowed since "
        "2023 as VRP compressed."))
    st.append(P("Methodology and data", "h2"))
    st += bullets([
        "<b>Sampling.</b> F&amp;O bhavcopies for the last trading day of every week, every monthly stock-option "
        "expiry and the following trading day (456 days, Jan-2020 to Nov-2026), in both the legacy and the UDiFF "
        "(from 8-Jul-2024) formats. Legacy lot sizes are recovered exactly as the GCD of open interest in shares. "
        "Time-series charts use the weekly snapshots only, smoothed with rolling medians because some snapshots "
        "fall on index-expiry days.",
        "<b>Implied vol.</b> Black-76 with the futures settlement price as forward; close price for traded "
        "contracts and NSE settlement price otherwise; OTM options with moneyness 0.7-1.3 and at least 3 days to expiry. ATM by "
        "linear interpolation in log-moneyness, 25-delta by interpolation in delta, constant maturity by total-"
        "variance interpolation.",
        "<b>Groups.</b> Top 30 = largest increase in average daily option notional between CY2020 and Jan-2023 to "
        "Nov-2024 (like the U.S. study, this uses in-sample information). Weights = trailing 63-day traded value.",
        "<b>EOV.</b> Average percentile rank of call volume/call OI and call volume/trailing 4-snapshot call "
        "volume; weekly cross-sectional OLS of return rank on EOV rank.",
        "<b>Backtests.</b> Entry at closing prices on the first trading day after each monthly expiry; ATM strike "
        "nearest the forward, both legs must have traded; daily delta hedge using Yahoo closes rescaled to the "
        "bhavcopy underlying; settled at the expiry-day close; Indian statutory costs plus slippage as described.",
    ])
    st.append(P("Limitations", "h2"))
    st += bullets([
        "Weekly sampling (not daily) for option-based metrics; EOV regressions are weekly rather than daily.",
        "No bid/ask quotes are available in bhavcopies; slippage is assumed (with a 2x sensitivity), and closing "
        "or settlement prices of thinly traded strikes can be noisy.",
        "Survivorship: nine F&amp;O names delisted or merged (e.g. HDFC, Mindtree) lack Yahoo prices and are "
        "excluded from price-dependent analysis. Corporate actions inside a holding period cause the trade to be "
        "dropped.",
        "Participant 'Client' includes HNIs and non-institutional corporates, not just small retail. 'Pro' "
        "includes HFT and arbitrage books.",
        "Backtests ignore margin financing, taxes on profits, and the capacity limits of single-stock option "
        "liquidity.",
    ])
    st.append(Spacer(1, 0.3 * cm))
    st.append(P(
        "<b>Disclaimer.</b> This document is an independent educational replication of a publicly circulated "
        "broker research framework, applied to public NSE data. It is an independent project, not affiliated with or endorsed by the authors of the original study. "
        "It is not investment advice or a recommendation to buy or sell any security or derivative. Options "
        "involve substantial risk; uncovered option selling can lose far more than the premium received. Past and "
        "simulated performance are not indicative of future results.", "small"))
    st.append(Spacer(1, 0.2 * cm))
    st.append(P("Code: india_retail_options/ (run_all.py reproduces every figure and table in this note).", "small"))

    doc.build(st)
    print(f"[pdf] wrote {C.REPORT_PDF}")


if __name__ == "__main__":
    build()
