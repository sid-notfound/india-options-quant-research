# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Normalise legacy and UDiFF F&O bhavcopies into one options/futures panel.

Output columns (one row per contract per sampled date):
  date, inst (OPTSTK/OPTIDX/FUTSTK/FUTIDX), symbol, expiry, strike, opt (CE/PE/FUT),
  close, settle, contracts, notional (Rs), oi (contracts), lot, und (underlying, NaN for legacy)
"""
import zipfile

import numpy as np
import pandas as pd

import config as C

UDIFF_MAP = {"STO": "OPTSTK", "IDO": "OPTIDX", "STF": "FUTSTK", "IDF": "FUTIDX"}


def _read(p) -> pd.DataFrame:
    with zipfile.ZipFile(p) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df


def parse_legacy(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "date": pd.to_datetime(df["TIMESTAMP"], format="%d-%b-%Y"),
        "inst": df["INSTRUMENT"].str.strip(),
        "symbol": df["SYMBOL"].str.strip(),
        "expiry": pd.to_datetime(df["EXPIRY_DT"], format="%d-%b-%Y"),
        "strike": df["STRIKE_PR"].astype(float),
        "opt": df["OPTION_TYP"].str.strip().replace({"XX": "FUT"}),
        "close": df["CLOSE"].astype(float),
        "settle": df["SETTLE_PR"].astype(float),
        "contracts": df["CONTRACTS"].astype(float),
        "notional": df["VAL_INLAKH"].astype(float) * 1e5,
        "oi_shares": df["OPEN_INT"].astype(float),
    })
    out = out[out["inst"].isin(UDIFF_MAP.values())]
    # Legacy files report OI in shares and carry no lot size: infer the lot from futures.
    fut = out[(out["opt"] == "FUT") & (out["contracts"] > 0)].copy()
    fut["lot"] = fut["notional"] / (fut["contracts"] * fut["close"])
    lots = fut.groupby("symbol")["lot"].median()
    out["lot"] = out["symbol"].map(lots)
    opt_traded = (out["opt"] != "FUT") & (out["contracts"] > 0) & out["lot"].isna()
    if opt_traded.any():
        q = out.loc[opt_traded, "notional"] / (out.loc[opt_traded, "strike"] + out.loc[opt_traded, "close"])
        approx = (q / out.loc[opt_traded, "contracts"]).groupby(out.loc[opt_traded, "symbol"]).median()
        out.loc[out["lot"].isna(), "lot"] = out.loc[out["lot"].isna(), "symbol"].map(approx)
    # Exact lot: OI in shares is always a multiple of the lot, so take the GCD per symbol.
    oi_int = out.loc[out["oi_shares"] > 0, ["symbol", "oi_shares"]].astype({"oi_shares": "int64"})
    gcd = oi_int.groupby("symbol")["oi_shares"].agg(lambda s: int(np.gcd.reduce(s.values)))
    est = out.groupby("symbol")["lot"].first()
    gcd = gcd.reindex(est.index)
    exact = gcd.where((gcd > 0.5 * est) & (gcd < 1.5 * est), est.round())
    out["lot"] = out["symbol"].map(exact).fillna(out["lot"].round())
    out["oi"] = out["oi_shares"] / out["lot"]
    out["und"] = np.nan
    return out.drop(columns="oi_shares")


def parse_udiff(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["FinInstrmTp"].isin(UDIFF_MAP)]
    lot = df["NewBrdLotQty"].astype(float)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["TradDt"]),
        "inst": df["FinInstrmTp"].map(UDIFF_MAP),
        "symbol": df["TckrSymb"].str.strip(),
        "expiry": pd.to_datetime(df["XpryDt"]),
        "strike": df["StrkPric"].fillna(0).astype(float),
        "opt": df["OptnTp"].fillna("FUT").replace({"": "FUT"}),
        "close": df["ClsPric"].astype(float),
        "settle": df["SttlmPric"].astype(float),
        "contracts": df["TtlTradgVol"].astype(float),
        "notional": df["TtlTrfVal"].astype(float),
        # UDiFF OpnIntrst is in shares (consistent with legacy); convert to contracts
        "oi": df["OpnIntrst"].astype(float) / lot,
        "lot": lot,
        "und": df["UndrlygPric"].astype(float),
    })
    return out


def parse_file(p) -> pd.DataFrame:
    df = _read(p)
    out = parse_legacy(df) if "INSTRUMENT" in df.columns else parse_udiff(df)
    out = out[(out["contracts"] > 0) | (out["oi"] > 0)]
    is_idx = out["inst"].isin(["OPTIDX", "FUTIDX"])
    out = out[~is_idx | out["symbol"].isin(C.INDEX_SYMBOLS)]
    return out


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Underlying (futures-implied for legacy), premium turnover and days-to-expiry."""
    fut = df[df["opt"] == "FUT"].sort_values("expiry")
    near = fut.groupby(["date", "symbol"]).first()
    t = (near["expiry"] - near.index.get_level_values("date")).dt.days / 365
    spot_from_fut = near["settle"] * np.exp(-C.RISK_FREE * t)
    key = pd.MultiIndex.from_frame(df[["date", "symbol"]])
    s = pd.Series(spot_from_fut.reindex(key).values, index=df.index)
    df["und"] = df["und"].where(df["und"] > 0, s)
    df["und"] = df["und"].fillna(df.groupby(["date", "symbol"])["und"].transform("median"))
    df["dte"] = (df["expiry"] - df["date"]).dt.days
    qty = df["contracts"] * df["lot"]
    is_opt = df["opt"] != "FUT"
    prem = (df["notional"] - df["strike"] * qty).where(is_opt)
    fallback = qty * df["close"]
    bad = prem.isna() | (prem < 0) | (prem > 3 * fallback + 1)
    df["premium"] = np.where(is_opt, np.where(bad, fallback, prem), np.nan)
    df["und_notional"] = qty * df["und"]  # "dollar volume" in the U.S. study sense
    return df


def run():
    cal = pd.read_csv(C.PROCESSED / "sample_calendar.csv", parse_dates=["date"])
    dates = sorted(cal["date"].unique())
    frames = []
    for i, d in enumerate(dates):
        p = C.RAW_FO / f"fo_{pd.Timestamp(d).strftime('%Y%m%d')}.csv.zip"
        if not p.exists():
            continue
        try:
            frames.append(parse_file(p))
        except Exception as e:  # noqa: BLE001
            print(f"[parse] failed {p.name}: {e}")
        if i % 100 == 0:
            print(f"[parse] {i}/{len(dates)}")
    df = pd.concat(frames, ignore_index=True)
    df = add_derived(df)
    for c in ("inst", "symbol", "opt"):
        df[c] = df[c].astype("category")
    for c in ("strike", "close", "settle", "contracts", "notional", "oi", "lot", "und", "premium", "und_notional"):
        df[c] = df[c].astype("float64")
    df.to_parquet(C.PROCESSED / "fo_panel.parquet", index=False)
    print(f"[parse] panel rows: {len(df):,}  dates: {df['date'].nunique()}  "
          f"stock symbols: {df.loc[df['inst'] == 'OPTSTK', 'symbol'].nunique()}")


if __name__ == "__main__":
    run()
