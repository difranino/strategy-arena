# ===================== STRATEGY ARENA — STOCKS (big tech basket) =====================
# Fighters trade NVDA, TSLA, AAPL, MSFT, AMZN, META, GOOGL, AMD, PLTR with $10,000 per position.
# "each" fighters run their rules on every stock; "cross" fighters compare the stocks with each other.
import numpy as np
import pandas as pd
from arena_core import condition, once_per_day, enter_exit, cross_up, cross_dn
from arena_strats import S
import arena_strats as NQ

STOCKS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AMD", "PLTR"]
MARKET = "SPY"
P = "{close:,.2f}"


def add_market_cols(dfs, mkt_df):
    """Give every stock the market's (SPY) state at the same bar, so rules can check the tide."""
    m = mkt_df[["close", "vwap", "dayret", "ret1h", "ema20"]].rename(columns=lambda c: "mkt_" + c)
    for a, d in dfs.items():
        mm = m.reindex(d.index).ffill()
        for c in mm.columns:
            d[c] = mm[c].values
        d["rs_day"] = d["dayret"] - d["mkt_dayret"]
        d["rs_1h"] = d["ret1h"] - d["mkt_ret1h"]
        d["mkt_up"] = d["mkt_close"] > d["mkt_vwap"]
        d["asset"] = a
    return dfs


# ---------------------------------------------------------------- cross-sectional helpers
def _panel(dfs, col):
    return pd.DataFrame({a: d[col] for a, d in dfs.items()})


def _pick_daily(dfs, score_col, at_k, n=1, largest=True, min_abs=0.0, side=1, label="rank"):
    """At bar k=at_k each day, pick the top/bottom n stocks by score_col and hold them to the close."""
    sc = _panel(dfs, score_col)
    k = next(iter(dfs.values()))["k"].reindex(sc.index)
    out = {a: np.zeros(len(d)) for a, d in dfs.items()}
    fresh = {a: np.zeros(len(d)) for a, d in dfs.items()}
    picks = pd.DataFrame(0, index=sc.index, columns=sc.columns)
    for ts in sc.index[k.values == at_k]:
        row = sc.loc[ts].dropna()
        if len(row) == 0:
            continue
        row = row[row.abs() >= min_abs] if min_abs else row
        chosen = (row.nlargest(n) if largest else row.nsmallest(n)).index
        picks.loc[ts, chosen] = side
    for a, d in dfs.items():
        p = picks[a].reindex(d.index).fillna(0).values
        kk = d["k"].values
        cur = 0.0
        t = np.zeros(len(d))
        f = np.zeros(len(d))
        for i in range(len(d)):
            if kk[i] == 0:
                cur = 0.0
            if p[i] != 0:
                cur = p[i]
                f[i] = p[i]
            t[i] = cur
        out[a], fresh[a] = t, f
    return {a: (out[a], fresh[a]) for a in dfs}


def _pair(dfs, a, b, entry=2.0, exit_=0.5, n=78, last_entry_k=23, flat_k=25):
    """Pairs trade: when a/b drifts far from normal, short the rich one and buy the cheap one."""
    out = {x: (np.zeros(len(d)), np.zeros(len(d))) for x, d in dfs.items()}
    if a not in dfs or b not in dfs:
        return out
    da, db = dfs[a], dfs[b]
    ix = da.index.intersection(db.index)
    ratio = np.log(da.close.reindex(ix) / db.close.reindex(ix))
    z = (ratio - ratio.rolling(n).mean()) / ratio.rolling(n).std()
    k = da["k"].reindex(ix).values
    pos = np.zeros(len(ix))
    cur = 0
    zz = z.values
    for i in range(len(ix)):
        if not np.isnan(zz[i]):
            if cur == 0 and zz[i] > entry and k[i] <= last_entry_k:
                cur = -1          # a is rich: short a, long b
            elif cur == 0 and zz[i] < -entry and k[i] <= last_entry_k:
                cur = 1           # a is cheap: long a, short b
            elif cur == -1 and zz[i] < exit_:
                cur = 0
            elif cur == 1 and zz[i] > -exit_:
                cur = 0
        if flat_k is not None and k[i] == flat_k:
            cur = 0
        pos[i] = cur
    zs = pd.Series(zz, index=ix)
    for x, sgn in ((a, 1), (b, -1)):
        d = dfs[x]
        d[f"pair_z_{a}_{b}"] = zs.reindex(d.index).values
        p = pd.Series(pos * sgn, index=ix).reindex(d.index).fillna(0).values
        out[x] = (p, np.zeros(len(d)))
    return out


# ---------------------------------------------------------------- the starting roster
def roster():
    L = []
    L.append(S("Strongest Stock of the Day", "Momentum",
               lambda dfs: _pick_daily(dfs, "rs_day", at_k=2, n=1, largest=True, side=1), scope="cross",
               about="At 10:15 New York, buys the stock beating the market by the most and holds it to the close.",
               why_l="Strongest of the 9 at 10:15: {dayret:+.2%} today vs the market {mkt_dayret:+.2%}.",
               watch="Picks the day's strongest stock at 10:15 New York (15:15 UK)."))
    L.append(S("Weakest Stock Short", "Momentum",
               lambda dfs: _pick_daily(dfs, "rs_day", at_k=2, n=1, largest=False, side=-1), scope="cross",
               about="At 10:15 New York, shorts the stock lagging the market by the most.",
               why_s="Weakest of the 9 at 10:15: {dayret:+.2%} today vs the market {mkt_dayret:+.2%}.",
               watch="Shorts the day's weakest stock at 10:15 New York (15:15 UK)."))
    L.append(S("Laggard Afternoon Bounce", "Reversal",
               lambda dfs: _pick_daily(dfs, "dayret", at_k=20, n=1, largest=False, min_abs=0.015, side=1), stop=1.5, scope="cross",
               about="At 14:30 New York, buys the biggest loser of the day (if it's down 1.5%+) for a late bounce.",
               why_l="Biggest loser of the 9 today ({dayret:+.2%}). Betting on a late-day bounce.",
               watch="Looks for the day's biggest loser at 14:30 New York (19:30 UK)."))
    L.append(S("Pairs: NVDA vs AMD", "Quant", lambda dfs: _pair(dfs, "NVDA", "AMD"), scope="cross",
               about="Chip rivals usually move together. When one runs too far ahead, short it and buy the other.",
               why_l="Pair trade: the NVDA/AMD gap stretched (z {pair_z_NVDA_AMD:+.1f}). Buying the cheap side.",
               why_s="Pair trade: the NVDA/AMD gap stretched (z {pair_z_NVDA_AMD:+.1f}). Shorting the rich side.",
               exit_l="The NVDA/AMD gap closed back to normal.", watch="Watching the NVDA/AMD price gap."))
    L.append(S("Pairs: GOOGL vs META", "Quant", lambda dfs: _pair(dfs, "GOOGL", "META"), scope="cross",
               about="Two ad giants. Trades the gap between them when it stretches.",
               why_l="Pair trade: the GOOGL/META gap stretched (z {pair_z_GOOGL_META:+.1f}). Buying the cheap side.",
               why_s="Pair trade: the GOOGL/META gap stretched (z {pair_z_GOOGL_META:+.1f}). Shorting the rich side.",
               exit_l="The GOOGL/META gap closed back to normal.", watch="Watching the GOOGL/META price gap."))
    L.append(S("Pairs: MSFT vs AAPL", "Quant", lambda dfs: _pair(dfs, "MSFT", "AAPL"), scope="cross",
               about="Two mega-caps that track each other. Trades the gap when it stretches.",
               why_l="Pair trade: the MSFT/AAPL gap stretched (z {pair_z_MSFT_AAPL:+.1f}). Buying the cheap side.",
               why_s="Pair trade: the MSFT/AAPL gap stretched (z {pair_z_MSFT_AAPL:+.1f}). Shorting the rich side.",
               exit_l="The MSFT/AAPL gap closed back to normal.", watch="Watching the MSFT/AAPL price gap."))
    L.append(S("ORB 15m (re-entry)", "Breakout",
               lambda d: once_per_day(d, d.close > d.orh1, d.close < d.orl1, start_k=1, last_entry_k=20), stop=1.5,
               about="Opening-range breakout on every stock, re-entering whenever price breaks out again.",
               why_l="Closed " + P + " above its 15-min opening high {orh1:,.2f}.",
               why_s="Closed " + P + " below its 15-min opening low {orl1:,.2f}.",
               watch="Waiting for a stock to break its opening range."))
    L.append(S("VWAP Reclaim with the Market", "Trend",
               lambda d: enter_exit(d, cross_up(d.close, d.vwap) & d.mkt_up & (d.k >= 2), d.close < d.vwap,
                                    cross_dn(d.close, d.vwap) & ~d.mkt_up & (d.k >= 2), d.close > d.vwap),
               stop=1.5, about="Buys a stock that climbs back over VWAP while the whole market is above its VWAP too.",
               why_l="Reclaimed VWAP {vwap:,.2f} while the market (SPY) is also above its VWAP.",
               why_s="Lost VWAP {vwap:,.2f} while the market (SPY) is also below its VWAP.",
               exit_l="Slipped back through VWAP.", watch="Waiting for a stock to reclaim VWAP with the market behind it."))
    L.append(S("Market-Filtered Breakout", "Breakout",
               lambda d: enter_exit(d, (d.close > d.dch20) & d.mkt_up, d.close < d.dcl10,
                                    (d.close < d.dcl20) & ~d.mkt_up, d.close > d.dch10),
               stop=2.0, about="20-bar breakouts, but only in the direction the market is going.",
               why_l="New 20-bar high at " + P + " and the market is with it.",
               why_s="New 20-bar low at " + P + " and the market is with it.",
               exit_l="Hit the 10-bar exit channel.", watch="Waiting for a breakout that agrees with the market."))
    L.append(S("Gap and Go (stocks)", "Momentum",
               lambda d: once_per_day(d, (d.k == 0) & (d.gap > 0.01) & (d.close > d.open),
                                      (d.k == 0) & (d.gap < -0.01) & (d.close < d.open), last_entry_k=0),
               stop=1.5, about="Rides a 1%+ opening gap when the first candle confirms it.",
               why_l="Gapped up {gap:+.2%} and the first candle confirmed it.",
               why_s="Gapped down {gap:+.2%} and the first candle confirmed it.",
               watch="Only trades 1%+ gaps at the open."))
    L.append(S("Gap Fill (stocks)", "Reversal",
               lambda d: enter_exit(d, (d.k == 0) & (d.gap < -0.01) & (d.close > d.open), d.close >= d.pdc,
                                    (d.k == 0) & (d.gap > 0.01) & (d.close < d.open), d.close <= d.pdc),
               stop=1.5, about="Fades a 1%+ gap once the first candle turns against it.",
               why_l="Gapped down {gap:+.2%} but the first candle turned up. Betting the gap fills to {pdc:,.2f}.",
               why_s="Gapped up {gap:+.2%} but the first candle turned down. Betting the gap fills to {pdc:,.2f}.",
               exit_l="Gap filled.", watch="Only trades 1%+ gaps that start to fade."))
    L.append(S("RSI(2) Dip in Uptrend (stocks)", "Reversal",
               lambda d: enter_exit(d, (d.rsi2 < 10) & (d.close > d.ema50) & d.mkt_up, d.rsi2 > 60),
               stop=1.5, about="Connors-style: buys sharp short-term dips in stocks that are trending up, when the market is OK.",
               why_l="RSI(2) crashed to {rsi2:.0f} in an uptrend, with the market above VWAP.",
               exit_l="RSI(2) recovered.", watch="Waiting for a sharp dip in an uptrending stock."))
    L.append(S("Power Hour Momentum", "Momentum",
               lambda d: once_per_day(d, (d.k == 22) & (d.dayret > 0.01) & (d.close > d.vwap),
                                      (d.k == 22) & (d.dayret < -0.01) & (d.close < d.vwap), start_k=22, last_entry_k=22),
               stop=1.5, about="At 15:00 New York, rides stocks with a strong day into the close.",
               why_l="Up {dayret:+.2%} on the day and above VWAP going into power hour.",
               why_s="Down {dayret:+.2%} on the day and below VWAP going into power hour.",
               watch="Decides at 15:00 New York (20:00 UK)."))
    L.append(S("Beta Catch-up", "Quant",
               lambda d: enter_exit(d, (d.mkt_ret1h > 0.004) & (d.rs_1h < -0.006) & (d.k >= 4) & (d.k <= 22),
                                    (d.rs_1h > 0) | (d.k >= 25),
                                    (d.mkt_ret1h < -0.004) & (d.rs_1h > 0.006) & (d.k >= 4) & (d.k <= 22),
                                    (d.rs_1h < 0) | (d.k >= 25)),
               stop=1.5, about="When the market jumps but a stock hasn't moved yet, buys it to catch up (and the reverse).",
               why_l="The market rose {mkt_ret1h:+.2%} in the last hour but this stock lagged by {rs_1h:+.2%}.",
               why_s="The market fell {mkt_ret1h:+.2%} in the last hour but this stock held up by {rs_1h:+.2%}.",
               exit_l="It caught up with the market.", watch="Waiting for a stock to fall behind a market move."))
    L.append(S("Opening Drive Fade", "Reversal",
               lambda d: once_per_day(d, (d.k == 2) & (d.dayret < -0.02) & (d.rsi14 < 30), (d.k == 2) & (d.dayret > 0.02) & (d.rsi14 > 70),
                                      start_k=2, last_entry_k=2),
               stop=1.5, tp=2.0, about="Fades a stock that ran 2%+ in the first 45 minutes with RSI stretched.",
               why_l="Dropped {dayret:+.2%} by 10:15 and RSI is {rsi14:.0f}. Fading the panic.",
               why_s="Ran {dayret:+.2%} by 10:15 and RSI is {rsi14:.0f}. Fading the euphoria.",
               watch="Decides at 10:15 New York (15:15 UK)."))
    L.append(S("Strong Close Overnight Hold", "Quant",
               lambda d: enter_exit(d, (d.k == 24) & (d.dayret > 0.005) & (d.day_pos > 0.85), d.k == 1),
               intraday=False, stop=3.0, about="Buys stocks closing near the top of their range on an up day and sells after the next open.",
               why_l="Closing near the day's high ({day_pos:.0%} of the range) on an up day ({dayret:+.2%}). Holding overnight.",
               exit_l="Next morning: overnight hold done.", watch="Decides at 15:45 New York (20:45 UK)."))
    L.append(S("EMA 9/21 (stocks)", "Trend", lambda d: condition(d, d.ema9 > d.ema21, d.ema9 < d.ema21), stop=2.0,
               about="Long while the 9 EMA is above the 21 EMA, short when below, on every stock.",
               why_l="9 EMA crossed above the 21 EMA.", why_s="9 EMA crossed below the 21 EMA.",
               exit_l="The EMAs crossed back.", watch="Waiting for EMA crosses."))
    return L


def pool():
    """Challengers waiting in the tunnel: classics that run on every stock."""
    keep = ["Bollinger Mean Reversion", "Keltner Channel Breakout", "Supertrend (10,3)", "MACD Crossover",
            "Ichimoku Cloud", "Stochastic 20/80", "Z-Score Stat Reversion", "Signal Ensemble (5-vote)"]
    lib = {s["name"]: s for s in NQ.original_roster()}
    out = [dict(lib[k]) for k in keep if k in lib]
    keep2 = ["Inside Bar Breakout", "NR4 Range Expansion", "Hull MA Trend", "Elder Impulse", "Volume Spike Momentum",
             "Range Expansion Bar", "Williams %R Reversal", "Pivot Bounce", "Camarilla H3/L3 Fade", "Triple EMA Stack 5/13/50"]
    lib2 = {s["name"]: s for s in NQ.challenger_pool()}
    out += [dict(lib2[k]) for k in keep2 if k in lib2]
    for s_ in out:
        s_["scope"] = "each"
    return out


def benchmark():
    return S("Hold the Basket", "Benchmark", lambda d: np.ones(len(d)), intraday=False,
             about="Holds $10,000 of each of the 9 stocks the whole time.", why_l="Always long.", watch="Always long.")
