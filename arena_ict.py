# ===================== STRATEGY ARENA — ICT / SMART MONEY / ORDER FLOW (Nasdaq tower) =====================
# Price-action ideas from ICT and Smart Money Concepts, turned into exact rules on 15-minute candles:
# fair value gaps, order blocks, break of structure, change of character, the Silver Bullet window,
# Judas swings, OTE retracements, and order-flow proxies.
# Honest note on order flow: free data has no bid/ask footprint, so "delta" here is estimated from each
# candle: volume x where it closed inside its range (close near the high = mostly buying).
# No peeking: every pattern is only known at the close of the candle that completes it.
import numpy as np
import pandas as pd
from arena_core import once_per_day, enter_exit
from arena_strats import S

P = "{close:,.2f}"


def _by_day(d, s, fn):
    return s.groupby(d["date"]).transform(fn)


def add_ict_cols(d):
    o, h, l, c, v = d.open.values, d.high.values, d.low.values, d.close.values, d.volume.values.astype(float)
    n = len(d)
    day = d["date"].values
    same2 = np.r_[False, False, day[2:] == day[:-2]]          # bar i and bar i-2 in the same session
    # ---------- fair value gaps (3-candle imbalance), known at the close of the 3rd candle
    h2, l2 = np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l[:-2]]
    bull = same2 & (l > h2)          # gap between candle 1's high and candle 3's low
    bear = same2 & (h < l2)
    d["fvg_bull"], d["fvg_bear"] = bull, bear
    # latest unfilled gap of the day (zone kept until price closes through it)
    bt = np.full(n, np.nan); bb = np.full(n, np.nan); st_ = np.full(n, np.nan); sb = np.full(n, np.nan)
    zt = zb = yt = yb = np.nan
    for i in range(n):
        if i and day[i] != day[i - 1]:
            zt = zb = yt = yb = np.nan
        if zb == zb and c[i] < zb:
            zt = zb = np.nan
        if yt == yt and c[i] > yt:
            yt = yb = np.nan
        if bull[i]:
            zt, zb = l[i], h2[i]
        if bear[i]:
            yt, yb = l2[i], h[i]
        bt[i], bb[i], st_[i], sb[i] = zt, zb, yt, yb
    d["bfvg_top"], d["bfvg_bot"], d["sfvg_top"], d["sfvg_bot"] = bt, bb, st_, sb
    # retest = a LATER candle dips into the gap and closes back out of it in the gap's direction
    prev_bt, prev_bb = np.r_[np.nan, bt[:-1]], np.r_[np.nan, bb[:-1]]
    prev_st, prev_sb = np.r_[np.nan, st_[:-1]], np.r_[np.nan, sb[:-1]]
    d["fvg_retest_long"] = (l <= prev_bt) & (c > prev_bt) & (c > o)
    d["fvg_retest_short"] = (h >= prev_sb) & (c < prev_sb) & (c < o)
    # ---------- displacement + order blocks (last opposite candle before a big move)
    atr = d.atr.values
    rng = h - l
    disp_up = (rng > 1.5 * atr) & (c > o) & (c > np.r_[np.nan, h[:-1]])
    disp_dn = (rng > 1.5 * atr) & (c < o) & (c < np.r_[np.nan, l[:-1]])
    obh = np.full(n, np.nan); obl = np.full(n, np.nan); sbh = np.full(n, np.nan); sbl = np.full(n, np.nan)
    ah = al = ch = cl = np.nan
    for i in range(1, n):
        if day[i] != day[i - 1]:
            ah = al = ch = cl = np.nan
        if al == al and c[i] < al:
            ah = al = np.nan
        if ch == ch and c[i] > ch:
            ch = cl = np.nan
        if disp_up[i] and day[i - 1] == day[i] and c[i - 1] < o[i - 1]:
            ah, al = h[i - 1], l[i - 1]
        if disp_dn[i] and day[i - 1] == day[i] and c[i - 1] > o[i - 1]:
            ch, cl = h[i - 1], l[i - 1]
        obh[i], obl[i], sbh[i], sbl[i] = ah, al, ch, cl
    d["bob_hi"], d["bob_lo"], d["sob_hi"], d["sob_lo"] = obh, obl, sbh, sbl
    p_obh, p_obl = np.r_[np.nan, obh[:-1]], np.r_[np.nan, obl[:-1]]
    p_sbh, p_sbl = np.r_[np.nan, sbh[:-1]], np.r_[np.nan, sbl[:-1]]
    d["ob_retest_long"] = (l <= p_obh) & (c > p_obh) & (c > o)
    d["ob_retest_short"] = (h >= p_sbl) & (c < p_sbl) & (c < o)
    # ---------- market structure: swing points (fractal, confirmed 2 candles later), BOS and CHoCH
    sh = np.full(n, np.nan); sl = np.full(n, np.nan)
    for i in range(4, n):
        j = i - 2
        if h[j] == max(h[j - 2:j + 3]) and day[j - 2] == day[i]:
            sh[i] = h[j]
        if l[j] == min(l[j - 2:j + 3]) and day[j - 2] == day[i]:
            sl[i] = l[j]
    last_sh = pd.Series(sh).groupby(day).ffill().values
    last_sl = pd.Series(sl).groupby(day).ffill().values
    p_sh, p_sl = np.r_[np.nan, last_sh[:-1]], np.r_[np.nan, last_sl[:-1]]
    bos_up = (c > p_sh) & (np.r_[np.nan, c[:-1]] <= p_sh)
    bos_dn = (c < p_sl) & (np.r_[np.nan, c[:-1]] >= p_sl)
    d["swing_hi"], d["swing_lo"] = last_sh, last_sl
    d["bos_up"], d["bos_dn"] = bos_up, bos_dn
    trend = np.zeros(n)
    t = 0
    for i in range(n):
        if i and day[i] != day[i - 1]:
            t = 0
        prev = t
        if bos_up[i]:
            t = 1
        elif bos_dn[i]:
            t = -1
        trend[i] = prev            # structure BEFORE this candle
    d["structure"] = trend
    d["choch_up"] = bos_up & (trend == -1)      # first break up after a downtrend
    d["choch_dn"] = bos_dn & (trend == 1)
    # ---------- day range so far, OTE zone, premium / discount
    dh = _by_day(d, d.high, "cummax").values
    dl = _by_day(d, d.low, "cummin").values
    d["day_hi"], d["day_lo"] = dh, dl
    leg = dh - dl
    d["pos_in_range"] = np.where(leg > 0, (c - dl) / leg, 0.5)
    d["ote_long"] = (leg > 2 * atr) & (d.pos_in_range.between(0.21, 0.38)) & (c > o) & (c > d.dopen.values)
    d["ote_short"] = (leg > 2 * atr) & (d.pos_in_range.between(0.62, 0.79)) & (c < o) & (c < d.dopen.values)
    # ---------- Judas swing: early fake move through yesterday's level, then back through the open
    f30h = d.groupby("date")["high"].transform(lambda s_: s_.iloc[:2].max()).values
    f30l = d.groupby("date")["low"].transform(lambda s_: s_.iloc[:2].min()).values
    k = d.k.values
    d["judas_short"] = (k >= 2) & (k <= 8) & (f30h > d.pdh.values) & (c < d.dopen.values)
    d["judas_long"] = (k >= 2) & (k <= 8) & (f30l < d.pdl.values) & (c > d.dopen.values)
    d["f30h"], d["f30l"] = f30h, f30l
    # ---------- order-flow proxies
    clv = np.where(rng > 0, (2 * c - h - l) / np.where(rng > 0, rng, 1), 0.0)
    delta = clv * v
    d["delta"] = delta
    d["cum_delta"] = pd.Series(delta, index=d.index).groupby(d["date"]).cumsum().values
    vol_avg = pd.Series(v, index=d.index).rolling(20, min_periods=5).mean().values
    d["vol_avg"] = vol_avg
    d["rel_vol"] = np.where(vol_avg > 0, v / vol_avg, 1.0)
    cd = d.cum_delta.values
    cd_hi = _by_day(d, d.cum_delta, "cummax").values
    cd_lo = _by_day(d, d.cum_delta, "cummin").values
    new_hi = (h >= dh) & (np.r_[np.nan, dh[:-1]] < h)
    new_lo = (l <= dl) & (np.r_[np.nan, dl[:-1]] > l)
    d["delta_div_short"] = new_hi & (cd < 0.8 * np.maximum(np.r_[0, cd_hi[:-1]], 1)) & (k >= 2)
    d["delta_div_long"] = new_lo & (cd > 0.8 * np.minimum(np.r_[0, cd_lo[:-1]], -1)) & (k >= 2)
    strong_buy = (clv > 0.5) & (d.rel_vol.values > 1.2)
    strong_sell = (clv < -0.5) & (d.rel_vol.values > 1.2)
    s3b = strong_buy & np.r_[False, strong_buy[:-1]] & np.r_[False, False, strong_buy[:-2]]
    s3s = strong_sell & np.r_[False, strong_sell[:-1]] & np.r_[False, False, strong_sell[:-2]]
    same3 = np.r_[False, False, day[2:] == day[:-2]]
    d["stacked_buy"], d["stacked_sell"] = s3b & same3, s3s & same3
    # absorption: big volume, tiny candle, right at a VWAP band
    small = rng < 0.6 * atr
    d["absorb_long"] = (d.rel_vol.values > 2.0) & small & (l <= d.vwap_l2.values) & (c > l + 0.5 * rng)
    d["absorb_short"] = (d.rel_vol.values > 2.0) & small & (h >= d.vwap_u2.values) & (c < h - 0.5 * rng)
    return d


def roster():
    """ICT / Smart Money / order-flow fighters for the Nasdaq tower."""
    L = []
    L.append(S("ICT Fair Value Gap Retest", "ICT",
               lambda d: once_per_day(d, d.fvg_retest_long & (d.close > d.vwap), d.fvg_retest_short & (d.close < d.vwap), start_k=1, last_entry_k=22),
               stop=1.0, tp=2.0, about="A fair value gap (3-candle imbalance) is left behind by a fast move. When price comes back into the gap "
                                       "and gets rejected, trade in the direction of the original move.",
               why_l="Price dipped into the bullish fair value gap ({bfvg_bot:,.2f}–{bfvg_top:,.2f}) and closed back above it, above VWAP.",
               why_s="Price rallied into the bearish fair value gap ({sfvg_bot:,.2f}–{sfvg_top:,.2f}) and closed back below it, below VWAP.",
               watch="Watching today's open fair value gaps for a retest."))
    L.append(S("SMC Order Block Bounce", "ICT",
               lambda d: once_per_day(d, d.ob_retest_long, d.ob_retest_short, start_k=1, last_entry_k=22),
               stop=1.0, tp=2.5, about="Smart money: the last opposite candle before a big displacement is an 'order block'. "
                                       "When price returns to it, expect the big players to defend it.",
               why_l="Back at the bullish order block ({bob_lo:,.2f}–{bob_hi:,.2f}) left before a big up-move, and it held.",
               why_s="Back at the bearish order block ({sob_lo:,.2f}–{sob_hi:,.2f}) left before a big down-move, and it held.",
               watch="Waiting for a displacement candle to mark a fresh order block."))
    L.append(S("SMC Break of Structure", "ICT",
               lambda d: once_per_day(d, d.bos_up & (d.structure >= 0) & (d.close > d.vwap), d.bos_dn & (d.structure <= 0) & (d.close < d.vwap),
                                      start_k=2, last_entry_k=20),
               stop=1.5, tp=2.5, about="Trend continuation: when price closes beyond the last swing point in the trend's direction, ride it.",
               why_l="Break of structure: closed " + P + " above the last swing high {swing_hi:,.2f}, trend up, above VWAP.",
               why_s="Break of structure: closed " + P + " below the last swing low {swing_lo:,.2f}, trend down, below VWAP.",
               watch="Tracking swing highs/lows: last high {swing_hi:,.2f}, last low {swing_lo:,.2f}."))
    L.append(S("SMC Change of Character", "ICT",
               lambda d: once_per_day(d, d.choch_up, d.choch_dn, start_k=3, last_entry_k=20),
               stop=1.5, tp=3.0, about="Reversal: after a downtrend, the FIRST close above a swing high is a 'change of character'. "
                                       "Catches the turn early.",
               why_l="Change of character: the downtrend just broke, closed above the swing high {swing_hi:,.2f}.",
               why_s="Change of character: the uptrend just broke, closed below the swing low {swing_lo:,.2f}.",
               watch="Waiting for a trend to break the other way."))
    L.append(S("ICT Silver Bullet (10-11am)", "ICT",
               lambda d: once_per_day(d, d.fvg_retest_long & (d.k >= 2) & (d.k <= 5) & (d.close > d.dopen),
                                      d.fvg_retest_short & (d.k >= 2) & (d.k <= 5) & (d.close < d.dopen), start_k=2, last_entry_k=5),
               stop=1.0, tp=2.0, about="ICT's Silver Bullet: only trades fair value gaps between 10:00 and 11:00 New York (15:00-16:00 UK), "
                                       "in the day's direction.",
               why_l="Silver Bullet window: bullish fair value gap retested at " + P + ", price above today's open.",
               why_s="Silver Bullet window: bearish fair value gap retested at " + P + ", price below today's open.",
               watch="Only active 10:00-11:00 New York (15:00-16:00 UK)."))
    L.append(S("ICT Judas Swing", "ICT",
               lambda d: once_per_day(d, d.judas_long, d.judas_short, start_k=2, last_entry_k=8),
               stop=1.5, tp=2.5, about="The open fakes one way (sweeping yesterday's high or low), then turns. When price comes back "
                                       "through today's open, trade the real direction.",
               why_l="Judas swing: the open dipped under yesterday's low {pdl:,.2f} (to {f30l:,.2f}) and price is back above today's open {dopen:,.2f}.",
               why_s="Judas swing: the open poked above yesterday's high {pdh:,.2f} (to {f30h:,.2f}) and price is back below today's open {dopen:,.2f}.",
               watch="Watching the first 30 minutes for a fake move through yesterday's range."))
    L.append(S("ICT OTE Retracement", "ICT",
               lambda d: once_per_day(d, d.ote_long & (d.structure >= 0), d.ote_short & (d.structure <= 0), start_k=3, last_entry_k=20),
               stop=1.0, tp=2.0, about="Optimal Trade Entry: after a strong leg, buy the 62-79% pullback (the 'discount') "
                                       "and sell the same zone in a down leg (the 'premium').",
               why_l="Pulled back into the OTE zone ({pos_in_range:.0%} of today's range {day_lo:,.2f}–{day_hi:,.2f}) and turned up.",
               why_s="Rallied into the OTE zone ({pos_in_range:.0%} of today's range {day_lo:,.2f}–{day_hi:,.2f}) and turned down.",
               watch="Today's range {day_lo:,.2f}–{day_hi:,.2f}; waiting for a 62-79% pullback."))
    L.append(S("Order Flow Delta Divergence", "OrderFlow",
               lambda d: once_per_day(d, d.delta_div_long, d.delta_div_short, start_k=2, last_entry_k=22),
               stop=1.0, tp=2.0, about="Price makes a new high of the day but buying pressure (estimated delta) doesn't: "
                                       "the move is running out of buyers. Fades it (and the mirror for lows).",
               why_l="New low of the day at {low:,.2f} but selling pressure is weaker than earlier. Fading the drop.",
               why_s="New high of the day at {high:,.2f} but buying pressure is weaker than earlier. Fading the pop.",
               watch="Comparing new highs/lows with estimated buying/selling pressure."))
    L.append(S("Order Flow Stacked Imbalance", "OrderFlow",
               lambda d: once_per_day(d, d.stacked_buy & (d.close > d.vwap), d.stacked_sell & (d.close < d.vwap), start_k=2, last_entry_k=20),
               stop=1.5, tp=2.5, about="Three candles in a row closing near their highs on above-average volume = aggressive buyers stacking up. "
                                       "Joins them (and the mirror for sellers).",
               why_l="3 candles in a row of strong buying on {rel_vol:.1f}x normal volume, above VWAP.",
               why_s="3 candles in a row of strong selling on {rel_vol:.1f}x normal volume, below VWAP.",
               watch="Waiting for 3 strong candles in a row on heavy volume."))
    L.append(S("Order Flow Absorption", "OrderFlow",
               lambda d: once_per_day(d, d.absorb_long, d.absorb_short, start_k=2, last_entry_k=22),
               stop=1.0, tp=2.0, about="Huge volume but the candle barely moves, right at a stretched VWAP band: someone big is "
                                       "absorbing the selling (or buying). Trades the bounce.",
               why_l="{rel_vol:.1f}x normal volume on a tiny candle at the lower VWAP band: sellers absorbed.",
               why_s="{rel_vol:.1f}x normal volume on a tiny candle at the upper VWAP band: buyers absorbed.",
               watch="Waiting for heavy volume with no price movement at a VWAP band."))
    for s_ in L:
        s_["scope"] = "each"
    return L
