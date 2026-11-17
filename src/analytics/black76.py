# Author: Siddhant Shukla <sidz0124@gmail.com>
"""Vectorised Black-76 pricing, greeks and implied volatility."""
import numpy as np
from scipy.special import ndtr

SQRT2PI = np.sqrt(2 * np.pi)


def _d1(F, K, T, sig):
    return (np.log(F / K) + 0.5 * sig ** 2 * T) / (sig * np.sqrt(T))


def price(F, K, T, sig, r, is_call):
    F, K, T, sig = map(np.asarray, (F, K, T, sig))
    d1 = _d1(F, K, T, sig)
    d2 = d1 - sig * np.sqrt(T)
    df = np.exp(-r * T)
    call = df * (F * ndtr(d1) - K * ndtr(d2))
    put = df * (K * ndtr(-d2) - F * ndtr(-d1))
    return np.where(is_call, call, put)


def delta(F, K, T, sig, r, is_call):
    """Delta with respect to the forward-equivalent spot (undiscounted N(d1))."""
    d1 = _d1(np.asarray(F), np.asarray(K), np.asarray(T), np.asarray(sig))
    return np.where(is_call, ndtr(d1), ndtr(d1) - 1.0)


def vega(F, K, T, sig, r):
    d1 = _d1(F, K, T, sig)
    return np.exp(-r * T) * F * np.exp(-0.5 * d1 ** 2) / SQRT2PI * np.sqrt(T)


def implied_vol(px, F, K, T, r, is_call, lo=0.01, hi=4.0, iters=60):
    """Bisection IV; NaN where the price violates no-arbitrage bounds."""
    px, F, K, T = (np.asarray(a, dtype=float) for a in (px, F, K, T))
    is_call = np.asarray(is_call, dtype=bool)
    df = np.exp(-r * T)
    intrinsic = np.where(is_call, np.maximum(F - K, 0), np.maximum(K - F, 0)) * df
    upper = np.where(is_call, F * df, K * df)
    valid = (px > intrinsic + 1e-8) & (px < upper) & (T > 0) & (F > 0) & (K > 0)
    a = np.full(px.shape, lo)
    b = np.full(px.shape, hi)
    for _ in range(iters):
        m = 0.5 * (a + b)
        pm = price(F, K, T, m, r, is_call)
        high = pm > px
        b = np.where(high, m, b)
        a = np.where(high, a, m)
    iv = 0.5 * (a + b)
    iv[~valid | (iv > hi * 0.99) | (iv < lo * 1.01)] = np.nan
    return iv
