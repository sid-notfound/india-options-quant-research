# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Sampled download of NSE F&O bhavcopies and participant-wise OI / volume files.

Sampling scheme:
  1. last trading day of every week (2020 -> today)
  2. every monthly stock-option expiry day
  3. the first trading day after each monthly expiry (strategy entry dates)
Expiry dates are discovered from the weekly files themselves (two-pass).
"""
import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pandas as pd
import requests

import config as C

ARCHIVE = "https://nsearchives.nseindia.com"
_session = requests.Session()
_session.headers.update(C.NSE_HEADERS)
MISSING_LOG = C.RAW_FO / "_missing.txt"


def _fo_url(d: date) -> str:
    if d < C.UDIFF_START:
        mon = d.strftime("%b").upper()
        return f"{ARCHIVE}/content/historical/DERIVATIVES/{d.year}/{mon}/fo{d.strftime('%d')}{mon}{d.year}bhav.csv.zip"
    return f"{ARCHIVE}/content/fo/BhavCopy_NSE_FO_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip"


def fo_path(d: date):
    return C.RAW_FO / f"fo_{d.strftime('%Y%m%d')}.csv.zip"


def _missing() -> set:
    if MISSING_LOG.exists():
        return set(MISSING_LOG.read_text().split())
    return set()


def _get(url: str, retries: int = 3):
    for i in range(retries):
        try:
            r = _session.get(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 200:
                return r.content
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def fetch_fo(d: date) -> bool:
    """Download the F&O bhavcopy for d. Returns True if the file exists locally afterwards."""
    p = fo_path(d)
    if p.exists():
        return True
    if d.strftime("%Y%m%d") in _missing():
        return False
    content = _get(_fo_url(d))
    time.sleep(C.DOWNLOAD_SLEEP)
    if content is None:
        with open(MISSING_LOG, "a") as f:
            f.write(d.strftime("%Y%m%d") + "\n")
        return False
    try:
        zipfile.ZipFile(io.BytesIO(content)).namelist()
    except zipfile.BadZipFile:
        return False
    p.write_bytes(content)
    return True


def fetch_participant(d: date):
    for kind in ("oi", "vol"):
        p = C.RAW_PART / f"fao_participant_{kind}_{d.strftime('%Y%m%d')}.csv"
        if p.exists():
            continue
        content = _get(f"{ARCHIVE}/content/nsccl/fao_participant_{kind}_{d.strftime('%d%m%Y')}.csv")
        time.sleep(C.DOWNLOAD_SLEEP)
        if content:
            p.write_bytes(content)


def last_trading_day_of_week(friday: date):
    """Walk back from Friday until a bhavcopy exists."""
    for k in range(5):
        d = friday - timedelta(days=k)
        if d < C.START or d > C.END:
            continue
        if fetch_fo(d):
            return d
    return None


def next_trading_day(d: date):
    for k in range(1, 6):
        n = d + timedelta(days=k)
        if n > C.END:
            return None
        if n.weekday() < 5 and fetch_fo(n):
            return n
    return None


def stock_expiries_from_file(p) -> set:
    with zipfile.ZipFile(p) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    if "INSTRUMENT" in df.columns:
        s = df.loc[df["INSTRUMENT"] == "OPTSTK", "EXPIRY_DT"]
        return set(pd.to_datetime(s, format="%d-%b-%Y").dt.date)
    s = df.loc[df["FinInstrmTp"] == "STO", "XpryDt"]
    return set(pd.to_datetime(s).dt.date)


def fridays():
    d = C.START + timedelta(days=(4 - C.START.weekday()) % 7)
    while d <= C.END + timedelta(days=4):
        yield d
        d += timedelta(days=7)


def run():
    print("[download] pass 1: weekly snapshots")
    with ThreadPoolExecutor(C.DOWNLOAD_THREADS) as ex:
        weekly = [d for d in ex.map(last_trading_day_of_week, list(fridays())) if d]
    print(f"[download] weekly files: {len(weekly)}")

    expiries = set()
    for d in weekly:
        expiries |= stock_expiries_from_file(fo_path(d))
    expiries = sorted(e for e in expiries if C.START <= e <= C.END)
    print(f"[download] pass 2: {len(expiries)} monthly expiries + entry days")

    def _expiry_pair(e):
        out = []
        ed = e
        for k in range(4):  # expiry falls on a holiday -> NSE moves it earlier
            cand = e - timedelta(days=k)
            if fetch_fo(cand):
                ed = cand
                out.append(("expiry", cand))
                break
        n = next_trading_day(ed)
        if n:
            out.append(("entry", n))
        return out

    with ThreadPoolExecutor(C.DOWNLOAD_THREADS) as ex:
        pairs = [x for lst in ex.map(_expiry_pair, expiries) for x in lst]

    rows = [("weekly", d) for d in weekly] + pairs
    cal = pd.DataFrame(rows, columns=["kind", "date"]).drop_duplicates()
    cal.to_csv(C.PROCESSED / "sample_calendar.csv", index=False)

    all_dates = sorted(set(cal["date"]))
    print(f"[download] participant files for {len(all_dates)} dates")
    with ThreadPoolExecutor(C.DOWNLOAD_THREADS) as ex:
        list(ex.map(fetch_participant, all_dates))
    print("[download] done")


if __name__ == "__main__":
    run()
