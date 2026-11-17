# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Indian F&O transaction costs (date-aware statutory rates + slippage assumptions)."""
import pandas as pd

STT_CHANGE = pd.Timestamp("2024-10-01")
TXN_CHANGE = pd.Timestamp("2024-10-01")


def option_sell_stt(d) -> float:
    return 0.001 if pd.Timestamp(d) >= STT_CHANGE else 0.000625


def futures_sell_stt(d) -> float:
    return 0.0002 if pd.Timestamp(d) >= STT_CHANGE else 0.000125


def option_exchange(d) -> float:
    return 0.0003503 if pd.Timestamp(d) >= TXN_CHANGE else 0.00053


FUT_EXCHANGE = 0.00002
GST = 0.18
STAMP_BUY_OPT = 0.00003
STAMP_BUY_FUT = 0.00002


def option_slippage(is_index: bool) -> float:
    """Half bid-ask as a fraction of premium."""
    return 0.005 if is_index else 0.015


FUT_SLIPPAGE = 0.0001


def option_trade_cost(premium: float, d, sell: bool, is_index: bool, slip_mult: float = 1.0) -> float:
    exch = option_exchange(d) * premium * (1 + GST)
    stt = option_sell_stt(d) * premium if sell else 0.0
    stamp = 0.0 if sell else STAMP_BUY_OPT * premium
    return exch + stt + stamp + slip_mult * option_slippage(is_index) * premium


def futures_trade_cost(notional_bought: float, notional_sold: float, d) -> float:
    traded = notional_bought + notional_sold
    return (FUT_EXCHANGE * traded * (1 + GST) + futures_sell_stt(d) * notional_sold
            + STAMP_BUY_FUT * notional_bought + FUT_SLIPPAGE * traded)
