# Author: Siddhant Shukla <sidz0124@gmail.com>
"""F&O stock universe, sector map and participant-wise data parsing."""
import io
import re

import pandas as pd
import requests

import config as C

SECTOR_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"


def sector_map() -> pd.Series:
    p = C.RAW_PRICES / "nifty500_sectors.csv"
    if not p.exists():
        r = requests.get(SECTOR_URL, headers=C.NSE_HEADERS, timeout=30)
        r.raise_for_status()
        p.write_bytes(r.content)
    df = pd.read_csv(p)
    m = df.set_index("Symbol")["Industry"]
    for old, new in C.YAHOO_RENAMES.items():
        if new in m.index and old not in m.index:
            m[old] = m[new]
    return m


def stock_universe(panel: pd.DataFrame) -> list:
    return sorted(panel.loc[panel["inst"] == "OPTSTK", "symbol"].astype(str).unique())


def _parse_participant_file(p) -> pd.DataFrame:
    text = p.read_text(errors="ignore")
    lines = [l for l in text.splitlines() if l.strip()]
    hdr_idx = next(i for i, l in enumerate(lines) if l.lower().startswith("client type"))
    df = pd.read_csv(io.StringIO("\n".join(lines[hdr_idx:])))
    df.columns = [re.sub(r"\s+", " ", c.replace('"', "")).strip() for c in df.columns]
    df = df[df["Client Type"].isin(["Client", "DII", "FII", "Pro", "TOTAL"])]
    df = df.set_index("Client Type").apply(pd.to_numeric, errors="coerce")
    return df


def participants() -> pd.DataFrame:
    """Long table: date, kind (oi/vol), participant, column, value."""
    rows = []
    for p in sorted(C.RAW_PART.glob("fao_participant_*.csv")):
        m = re.match(r"fao_participant_(oi|vol)_(\d{8})\.csv", p.name)
        if not m:
            continue
        try:
            df = _parse_participant_file(p)
        except Exception:  # noqa: BLE001
            continue
        s = df.stack().rename("value").reset_index()
        s.columns = ["participant", "field", "value"]
        s["kind"] = m.group(1)
        s["date"] = pd.to_datetime(m.group(2))
        rows.append(s)
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(C.PROCESSED / "participants.parquet", index=False)
    return out
