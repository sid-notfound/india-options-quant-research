# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Retail evidence from NSE participant-wise volume and open interest (U.S. study Figs 12-16 analogue)."""
import pandas as pd

import config as C
from src.analytics import common as cm

PARTS = ["Client", "Pro", "FII", "DII"]


def _wide(kind: str) -> pd.DataFrame:
    p = pd.read_parquet(C.PROCESSED / "participants.parquet")
    p = p[(p["kind"] == kind) & p["date"].isin(cm.weekly_dates())]
    return p.pivot_table(index="date", columns=["participant", "field"], values="value", aggfunc="first")


def run() -> dict:
    vol, oi = _wide("vol"), _wide("oi")
    out = pd.DataFrame(index=vol.index)
    for seg, pre in (("idx", "Option Index"), ("stk", "Option Stock")):
        legs = [f"{pre} Call Long", f"{pre} Call Short", f"{pre} Put Long", f"{pre} Put Short"]
        tot = vol["TOTAL"][legs].sum(axis=1)
        for who in PARTS:
            out[f"share_{who}_{seg}"] = vol[who][legs].sum(axis=1) / tot
        for who in ("Client", "FII", "Pro"):
            out[f"call_bs_ratio_{who}_{seg}"] = vol[who][f"{pre} Call Long"] / vol[who][f"{pre} Call Short"]
            out[f"net_call_oi_{who}_{seg}"] = oi[who][f"{pre} Call Long"] - oi[who][f"{pre} Call Short"]
            out[f"net_put_oi_{who}_{seg}"] = oi[who][f"{pre} Put Long"] - oi[who][f"{pre} Put Short"]
        out[f"client_long_call_oi_share_{seg}"] = oi["Client"][f"{pre} Call Long"] / oi["TOTAL"][f"{pre} Call Long"]
        out[f"total_contracts_{seg}"] = tot / 2
    out = out.sort_index()
    out.to_parquet(C.PROCESSED / "res_participants.parquet")

    peak = slice(*C.PEAK_PERIOD)
    s = {}
    for seg in ("idx", "stk"):
        for who in ("Client", "Pro", "FII"):
            s[f"share_{who}_{seg}_2020"] = out.loc["2020", f"share_{who}_{seg}"].mean()
            s[f"share_{who}_{seg}_peak"] = out.loc[peak, f"share_{who}_{seg}"].mean()
            s[f"share_{who}_{seg}_last6m"] = out[f"share_{who}_{seg}"].iloc[-26:].mean()
        s[f"client_call_bs_{seg}_2020"] = out.loc["2020", f"call_bs_ratio_Client_{seg}"].mean()
        s[f"client_call_bs_{seg}_peak"] = out.loc[peak, f"call_bs_ratio_Client_{seg}"].mean()
        s[f"fii_call_bs_{seg}_peak"] = out.loc[peak, f"call_bs_ratio_FII_{seg}"].mean()
        s[f"client_net_call_oi_{seg}_peak"] = out.loc[peak, f"net_call_oi_Client_{seg}"].mean()
        s[f"fii_net_call_oi_{seg}_peak"] = out.loc[peak, f"net_call_oi_FII_{seg}"].mean()
        s[f"client_long_call_oi_share_{seg}_peak"] = out.loc[peak, f"client_long_call_oi_share_{seg}"].mean()
    cm.save_result("participants", s)
    return s


if __name__ == "__main__":
    print(run())
