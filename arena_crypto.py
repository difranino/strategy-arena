# ===================== STRATEGY ARENA — CRYPTO (BTC, ETH, SOL, 24/7) =====================
# $10,000 per position, 0.15% round-trip costs. One "session" = one UK calendar day; knockouts at 00:00 UK.
import numpy as np
import pandas as pd
from arena_core import condition, once_per_day, enter_exit, cross_up, cross_dn
from arena_strats import S
import arena_strats as NQ
from arena_stocks import _pair

COINS = ["BTC-USD", "ETH-USD", "SOL-USD"]
P = "{close:,.2f}"


def add_crypto_cols(dfs):
    """Shared features: BTC's last-hour move on every coin, and the move since the US stock open."""
    btc = dfs.get("BTC-USD")
    for a, d in dfs.items():
        d["asset"] = a
        if btc is not None:
            d["btc_ret1h"] = btc["ret1h"].reindex(d.index).ffill().values
        # price at the US stock-market open (9:30 New York) each UK day, known from that bar onward
        op = d["open"].where(d.ny_mins == 570)
        d["us_open_px"] = op.groupby(d["date"]).transform(lambda s_: s_.ffill())
        d["us_move"] = d.close / d.us_open_px - 1
        d["weekend"] = d.index.dayofweek >= 5
        d["ema1h_up"] = d.ema_1h20.diff() > 0
    return dfs


def _lead_lag(dfs, thresh=0.008, hold=4):
    """BTC moves first: if BTC jumps but an alt hasn't followed yet, buy the alt for an hour (and the reverse)."""
    out = {}
    for a, d in dfs.items():
        if a == "BTC-USD":
            out[a] = np.zeros(len(d))
            continue
        b, r = d.btc_ret1h.values, d.ret1h.values
        t = np.zeros(len(d))
        f = np.zeros(len(d))
        left = 0
        cur = 0
        for i in range(len(d)):
            if left > 0:
                left -= 1
                if left == 0:
                    cur = 0
            if cur == 0 and not np.isnan(b[i]) and not np.isnan(r[i]):
                if b[i] > thresh and r[i] < b[i] / 2:
                    cur, left, f[i] = 1, hold, 1
                elif b[i] < -thresh and r[i] > b[i] / 2:
                    cur, left, f[i] = -1, hold, -1
            t[i] = cur
        out[a] = (t, f)
    return out


def roster():
    L = []
    L.append(S("London Open Breakout", "Breakout",
               lambda d: once_per_day(d, d.close > d.asia_h, d.close < d.asia_l, start_k=28, last_entry_k=48), stop=1.5,
               about="Classic crypto session play: the quiet Asia range (00:00-07:00 UK) often breaks when London opens.",
               why_l="Broke above the Asia-session high {asia_h:,.2f} after London opened.",
               why_s="Broke below the Asia-session low {asia_l:,.2f} after London opened.",
               watch="Asia range {asia_l:,.2f} – {asia_h:,.2f}. Trades breaks from 07:00 to 12:00 UK."))
    L.append(S("US Open Momentum (crypto)", "Momentum",
               lambda d: enter_exit(d, (d.ny_mins == 585) & (d.us_move > 0.003), d.ny_mins >= 13 * 60 + 45,
                                    (d.ny_mins == 585) & (d.us_move < -0.003), d.ny_mins >= 13 * 60 + 45),
               stop=1.5, about="When US stocks open, crypto often picks a direction. Follows the first 30 minutes for 4 hours.",
               why_l="US stocks opened and this coin rose {us_move:+.2%} in the first 30 minutes. Riding it.",
               why_s="US stocks opened and this coin fell {us_move:+.2%} in the first 30 minutes. Riding it.",
               exit_l="4 hours after the US open, time's up.", watch="Decides 30 minutes after the US stock open (about 15:00 UK)."))
    L.append(S("Daily Open Reclaim", "Trend",
               lambda d: enter_exit(d, cross_up(d.close, d.dopen) & d.ema1h_up, d.close < d.dopen,
                                    cross_dn(d.close, d.dopen) & ~d.ema1h_up, d.close > d.dopen),
               stop=1.5, about="Crypto traders watch the daily open. Buys a reclaim of it with the hourly trend rising.",
               why_l="Climbed back above today's open {dopen:,.2f} with the hourly trend rising.",
               why_s="Fell back below today's open {dopen:,.2f} with the hourly trend falling.",
               exit_l="Lost the daily open again.", watch="Today's open is {dopen:,.2f}. Waiting for a reclaim or a loss of it."))
    L.append(S("BTC Leads the Alts", "Quant", lambda dfs: _lead_lag(dfs), scope="cross",
               about="Bitcoin usually moves first. When BTC jumps and ETH/SOL haven't caught up, buy them for an hour.",
               why_l="BTC moved {btc_ret1h:+.2%} in an hour but this coin only {ret1h:+.2%}. Expecting it to catch up.",
               why_s="BTC dropped {btc_ret1h:+.2%} in an hour but this coin only {ret1h:+.2%}. Expecting it to follow.",
               exit_l="One hour passed.", watch="Watching for BTC to move first."))
    L.append(S("ETH/BTC Ratio Reversion", "Quant",
               lambda dfs: _pair(dfs, "ETH-USD", "BTC-USD", entry=2.2, n=192, last_entry_k=99, flat_k=None),
               scope="cross", intraday=False, stop=4.0,
               about="ETH and BTC move together. When the ETH/BTC ratio stretches, bet on it snapping back.",
               why_l="Pair trade: the ETH/BTC ratio stretched (z {pair_z_ETH-USD_BTC-USD:+.1f}). Buying the cheap side.",
               why_s="Pair trade: the ETH/BTC ratio stretched (z {pair_z_ETH-USD_BTC-USD:+.1f}). Shorting the rich side.",
               exit_l="The ETH/BTC ratio returned to normal.", watch="Watching the ETH/BTC ratio."))
    L.append(S("SOL/ETH Ratio Reversion", "Quant",
               lambda dfs: _pair(dfs, "SOL-USD", "ETH-USD", entry=2.2, n=192, last_entry_k=99, flat_k=None),
               scope="cross", intraday=False, stop=4.0,
               about="Same idea for SOL vs ETH.",
               why_l="Pair trade: the SOL/ETH ratio stretched. Buying the cheap side.",
               why_s="Pair trade: the SOL/ETH ratio stretched. Shorting the rich side.",
               exit_l="The SOL/ETH ratio returned to normal.", watch="Watching the SOL/ETH ratio."))
    L.append(S("Liquidation Wick Reversal", "Reversal",
               lambda d: once_per_day(d, (d.lower_wick > 2 * d.atr) & (d.close > d.open), (d.upper_wick > 2 * d.atr) & (d.close < d.open)),
               stop=1.0, tp=2.0, about="A huge wick usually means forced liquidations that got bought (or sold) right back. Trades the snap-back.",
               why_l="Huge lower wick to {low:,.2f} (liquidations) and it closed green. Buying the snap-back.",
               why_s="Huge upper wick to {high:,.2f} (short squeeze) and it closed red. Selling the snap-back.",
               watch="Waiting for a liquidation wick."))
    L.append(S("4h Trend Rider", "Trend",
               lambda d: condition(d, (d.ema_4h20 > d.ema_4h50) & (d.close > d.ema_4h20), (d.ema_4h20 < d.ema_4h50) & (d.close < d.ema_4h20)),
               intraday=False, stop=3.0, about="Swing trend follower on the 4-hour EMAs. Holds for days.",
               why_l="4h trend up: 20 EMA {ema_4h20:,.2f} above 50 EMA {ema_4h50:,.2f}, price above both.",
               why_s="4h trend down: 20 EMA {ema_4h20:,.2f} below 50 EMA {ema_4h50:,.2f}, price below both.",
               exit_l="Price fell back through the 4h 20 EMA.", watch="Waiting for the 4h trend to line up."))
    L.append(S("1-Day Breakout (crypto Turtle)", "Breakout",
               lambda d: enter_exit(d, d.close > d.dch_day, d.close < d.dcl_half, d.close < d.dcl_day, d.close > d.dch_half),
               intraday=False, stop=2.5, about="Turtle rules on crypto: a new 24-hour high or low, exit on a 12-hour channel.",
               why_l="New 24-hour high at " + P + ".", why_s="New 24-hour low at " + P + ".",
               exit_l="Hit the 12-hour exit channel.", watch="24h range {dcl_day:,.2f} – {dch_day:,.2f}."))
    L.append(S("Weekend VWAP Fade", "Reversal",
               lambda d: enter_exit(d, d.weekend & (d.close < d.vwap_l2), d.close >= d.vwap, d.weekend & (d.close > d.vwap_u2), d.close <= d.vwap),
               stop=1.5, about="Weekends are thin and choppy. Fades stretches away from VWAP on Saturdays and Sundays.",
               why_l="Weekend stretch: " + P + " is far below VWAP {vwap:,.2f}.",
               why_s="Weekend stretch: " + P + " is far above VWAP {vwap:,.2f}.",
               exit_l="Back at VWAP.", watch="Only trades on weekends."))
    lib = {s_["name"]: s_ for s_ in NQ.original_roster()}
    lib2 = {s_["name"]: s_ for s_ in NQ.challenger_pool()}
    for k_, swing in [("Supertrend (10,3)", True), ("MACD Crossover", True), ("RSI(2) Connors", False),
                      ("Bollinger Squeeze Breakout", False), ("Z-Score Stat Reversion", False)]:
        L.append(dict(lib[k_], intraday=not swing, scope="each"))
    L.append(dict(lib2["Volume Spike Momentum"], scope="each"))
    for s_ in L:
        s_["market"] = "crypto"
    return L


def pool():
    lib = {s_["name"]: s_ for s_ in NQ.original_roster()}
    lib2 = {s_["name"]: s_ for s_ in NQ.challenger_pool()}
    names1 = ["Keltner Channel Breakout", "Ichimoku Cloud", "Heikin-Ashi Trend", "Stochastic 20/80", "VWAP Mean Reversion",
              "Donchian Breakout (Turtle)", "EMA Crossover 9/21"]
    names2 = ["Hull MA Trend", "KAMA Adaptive Trend", "Elder Impulse", "Aroon Trend", "Vortex Indicator", "TRIX Signal Cross",
              "Williams %R Reversal", "CCI ±100 Reversal", "MFI 20/80 Reversal", "Inside Bar Breakout", "NR4 Range Expansion",
              "Engulfing Reversal", "Chandelier Exit Trend", "Oscillator Ensemble"]
    out = [dict(lib[n]) for n in names1 if n in lib] + [dict(lib2[n]) for n in names2 if n in lib2]
    for s_ in out:
        s_["scope"], s_["market"] = "each", "crypto"
    return out


def benchmark():
    return S("Hold the Coins", "Benchmark", lambda d: np.ones(len(d)), intraday=False, market="crypto",
             about="Holds $10,000 each of BTC, ETH and SOL the whole time.", why_l="Always long.", watch="Always long.")
