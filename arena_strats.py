# ===================== NASDAQ STRATEGY ARENA — fighters =====================
# Each fighter = a well-known strategy + plain-English reasons for what it does.
# why_l / why_s: why it went long / short.  exit_l / exit_s: why its own exit rule fired.
# watch: what it is waiting for while flat.  Values in {braces} are filled from the bar it decided on.
import numpy as np
from arena_core import condition, once_per_day, enter_exit, cross_up, cross_dn

P = "{close:,.2f}"


def S(name, family, fn, stop=None, tp=None, intraday=True, about="", why_l="", why_s="",
      exit_l="", exit_s="", watch="", once=False, scope="each", market=None, assets=None):
    """scope: "each" = the rules run on every asset in the arena separately;
    "cross" = fn(dict of asset dataframes) -> {asset: target}, for rules that compare assets."""
    return dict(name=name, family=family, fn=fn, stop=stop, tp=tp, intraday=intraday, about=about,
                why_l=why_l, why_s=why_s, exit_l=exit_l, exit_s=exit_s or exit_l, watch=watch, once=once,
                scope=scope, market=market, assets=assets)


def by_name(*libs):
    out = {}
    for lib in libs:
        for s_ in lib():
            out[s_["name"]] = s_
    return out


# ============================================================ starting roster (season 1)
def original_roster():
    L = []
    L.append(S("Opening Range Breakout 15m", "Breakout",
               lambda d: once_per_day(d, d.close > d.orh1, d.close < d.orl1, start_k=1), stop=1.5, once=True,
               about="Trades the first close outside the 9:30-9:45 range.",
               why_l="Closed " + P + " above the 15-min opening high {orh1:,.2f}. Breakout up.",
               why_s="Closed " + P + " below the 15-min opening low {orl1:,.2f}. Breakout down.",
               watch="Waiting for a close outside the opening range {orl1:,.2f} – {orh1:,.2f}."))
    L.append(S("Opening Range Breakout 30m", "Breakout",
               lambda d: once_per_day(d, d.close > d.orh2, d.close < d.orl2, start_k=2), stop=1.5, once=True,
               about="Same idea with the first 30 minutes.",
               why_l="Closed " + P + " above the 30-min opening high {orh2:,.2f}.",
               why_s="Closed " + P + " below the 30-min opening low {orl2:,.2f}.",
               watch="Waiting for a close outside the 30-min range {orl2:,.2f} – {orh2:,.2f}."))
    L.append(S("Initial Balance Breakout (1h)", "Breakout",
               lambda d: once_per_day(d, d.close > d.orh4, d.close < d.orl4, start_k=4), stop=1.5, once=True,
               about="Market-profile classic: break of the first hour's range.",
               why_l="Closed " + P + " above the first-hour high {orh4:,.2f}.",
               why_s="Closed " + P + " below the first-hour low {orl4:,.2f}.",
               watch="Waiting for a break of the first-hour range {orl4:,.2f} – {orh4:,.2f}."))
    L.append(S("Opening Range Fade", "Reversal",
               lambda d: once_per_day(d, (d.low < d.orl2) & (d.close > d.orl2), (d.high > d.orh2) & (d.close < d.orh2), start_k=2),
               stop=1.0, tp=2.0, once=True, about="Failed breakout of the 30m range, trade back inside.",
               why_l="Dipped to {low:,.2f} below the 30-min low {orl2:,.2f} but closed back inside at " + P + ". Failed breakdown.",
               why_s="Poked to {high:,.2f} above the 30-min high {orh2:,.2f} but closed back inside at " + P + ". Failed breakout.",
               watch="Waiting for a fake-out beyond {orl2:,.2f} or {orh2:,.2f} that snaps back inside."))
    L.append(S("NY Open Momentum", "Momentum",
               lambda d: once_per_day(d, (d.k == 0) & (d.close > d.open), (d.k == 0) & (d.close < d.open), last_entry_k=0),
               stop=1.5, once=True, about="Follows the direction of the first 15-minute candle.",
               why_l="First candle closed up (" + P + " vs open {open:,.2f}). Riding the opening push.",
               why_s="First candle closed down (" + P + " vs open {open:,.2f}). Riding the opening drop.",
               watch="Only trades the first candle of the day. Back tomorrow."))
    L.append(S("Prior Day High/Low Breakout", "Breakout",
               lambda d: once_per_day(d, d.close > d.pdh, d.close < d.pdl), stop=1.5, once=True,
               about="Break of yesterday's high or low.",
               why_l="Closed " + P + " above yesterday's high {pdh:,.2f}.",
               why_s="Closed " + P + " below yesterday's low {pdl:,.2f}.",
               watch="Waiting for a close above {pdh:,.2f} or below {pdl:,.2f} (yesterday's range)."))
    L.append(S("Liquidity Sweep Reversal (SMC)", "Reversal",
               lambda d: once_per_day(d, (d.low < d.pdl) & (d.close > d.pdl), (d.high > d.pdh) & (d.close < d.pdh)),
               stop=1.0, tp=2.5, once=True, about="Smart-money style: wick through yesterday's level, close back inside, reverse.",
               why_l="Swept the stops under yesterday's low {pdl:,.2f} (wick to {low:,.2f}) and closed back above at " + P + ".",
               why_s="Swept the stops above yesterday's high {pdh:,.2f} (wick to {high:,.2f}) and closed back below at " + P + ".",
               watch="Waiting for a stop-hunt through {pdl:,.2f} or {pdh:,.2f} that closes back inside."))
    L.append(S("Gap Fill", "Reversal",
               lambda d: enter_exit(d, (d.k == 0) & (d.gap < -0.0015), d.close >= d.pdc,
                                    (d.k == 0) & (d.gap > 0.0015), d.close <= d.pdc),
               stop=1.5, about="Fades an opening gap above 0.15% back toward yesterday's close.",
               why_l="Opened {open:,.2f}, gapped down from yesterday's close {pdc:,.2f}. Betting the gap fills.",
               why_s="Opened {open:,.2f}, gapped up from yesterday's close {pdc:,.2f}. Betting the gap fills.",
               exit_l="Gap filled: price got back to yesterday's close {pdc:,.2f}.",
               watch="Only trades a gap bigger than 0.15% at the open."))
    L.append(S("Gap and Go", "Momentum",
               lambda d: once_per_day(d, (d.k == 0) & (d.gap > 0.0015) & (d.close > d.open),
                                      (d.k == 0) & (d.gap < -0.0015) & (d.close < d.open), last_entry_k=0),
               stop=1.5, once=True, about="Rides a gap when the first candle confirms it.",
               why_l="Gapped up and the first candle confirmed it, closing up at " + P + ".",
               why_s="Gapped down and the first candle confirmed it, closing down at " + P + ".",
               watch="Only trades a confirmed opening gap. Back tomorrow."))
    L.append(S("Volatility Breakout (L. Williams)", "Breakout",
               lambda d: once_per_day(d, d.close > d.lw_up, d.close < d.lw_dn), stop=1.5, once=True,
               about="Long above open + half of yesterday's range, short below.",
               why_l="Closed " + P + " above the volatility trigger {lw_up:,.2f} (open + half yesterday's range).",
               why_s="Closed " + P + " below the volatility trigger {lw_dn:,.2f} (open − half yesterday's range).",
               watch="Triggers at {lw_up:,.2f} (long) or {lw_dn:,.2f} (short)."))
    L.append(S("Intraday Momentum (last 30 min)", "Quant", lambda d: _last_half_hour(d),
               about="Research-based: the first-30-min return predicts the last 30 min.",
               why_l="The first 30 minutes were up ({first30:+.2%} vs yesterday). History says the last half hour follows.",
               why_s="The first 30 minutes were down ({first30:+.2%} vs yesterday). History says the last half hour follows.",
               watch="Sleeps until 15:15 New York (20:15 UK), then trades the last 30 minutes."))
    L.append(S("VWAP Mean Reversion", "Reversal",
               lambda d: enter_exit(d, d.close < d.vwap_l2, d.close >= d.vwap, d.close > d.vwap_u2, d.close <= d.vwap),
               stop=1.5, about="Buys 2 SD below VWAP and sells 2 SD above, exiting at VWAP.",
               why_l="Stretched to " + P + ", more than 2 standard deviations below VWAP {vwap:,.2f}. Expecting a snap back.",
               why_s="Stretched to " + P + ", more than 2 standard deviations above VWAP {vwap:,.2f}. Expecting a snap back.",
               exit_l="Back at VWAP {vwap:,.2f}. Job done.",
               watch="Waiting for a stretch beyond {vwap_l2:,.2f} or {vwap_u2:,.2f} (VWAP ± 2 SD)."))
    L.append(S("VWAP Trend Pullback", "Trend",
               lambda d: enter_exit(d, (d.close > d.vwap) & (d.ema9 > d.ema21) & (d.low.shift() <= d.ema21.shift()) & (d.close > d.ema9),
                                    d.close < d.vwap,
                                    (d.close < d.vwap) & (d.ema9 < d.ema21) & (d.high.shift() >= d.ema21.shift()) & (d.close < d.ema9),
                                    d.close > d.vwap),
               stop=1.5, about="With the trend above VWAP, buys pullbacks to the 21 EMA.",
               why_l="Uptrend above VWAP {vwap:,.2f}. Price pulled back to the 21 EMA and bounced to " + P + ".",
               why_s="Downtrend below VWAP {vwap:,.2f}. Price rallied to the 21 EMA and rolled over to " + P + ".",
               exit_l="Price crossed back through VWAP {vwap:,.2f}, so the trend is broken.",
               watch="Waiting for a pullback to the 21 EMA ({ema21:,.2f}) in a VWAP trend."))
    L.append(S("EMA Crossover 9/21", "Trend", lambda d: condition(d, d.ema9 > d.ema21, d.ema9 < d.ema21), stop=2.0,
               about="Long while the 9 EMA is above the 21 EMA, short when below.",
               why_l="9 EMA ({ema9:,.2f}) crossed above 21 EMA ({ema21:,.2f}).",
               why_s="9 EMA ({ema9:,.2f}) crossed below 21 EMA ({ema21:,.2f}).",
               exit_l="The EMAs crossed the other way.", watch="Waiting for the 9 EMA to cross the 21 EMA."))
    L.append(S("EMA Trend 20/50", "Trend", lambda d: condition(d, d.ema20 > d.ema50, d.ema20 < d.ema50), stop=2.0,
               about="Slower trend filter.",
               why_l="20 EMA ({ema20:,.2f}) is above the 50 EMA ({ema50:,.2f}), so the trend is up.",
               why_s="20 EMA ({ema20:,.2f}) is below the 50 EMA ({ema50:,.2f}), so the trend is down.",
               exit_l="The 20/50 EMAs crossed.", watch="Waiting for the 20 EMA to cross the 50 EMA."))
    L.append(S("MACD Crossover", "Trend", lambda d: condition(d, d.macd > d.macds, d.macd < d.macds), stop=2.0,
               about="MACD above the signal line goes long, below goes short.",
               why_l="MACD ({macd:.1f}) crossed above its signal line ({macds:.1f}).",
               why_s="MACD ({macd:.1f}) crossed below its signal line ({macds:.1f}).",
               exit_l="MACD crossed back.", watch="Waiting for a MACD cross."))
    L.append(S("Supertrend (10,3)", "Trend", lambda d: condition(d, d.st_dir > 0, d.st_dir < 0),
               about="Popular TradingView trend follower.",
               why_l="Supertrend flipped green. Price " + P + " broke above the band.",
               why_s="Supertrend flipped red. Price " + P + " broke below the band.",
               exit_l="Supertrend flipped.", watch="Waiting for a Supertrend flip."))
    L.append(S("Parabolic SAR", "Trend", lambda d: condition(d, d.psar_dir > 0, d.psar_dir < 0),
               about="Welles Wilder's stop-and-reverse.",
               why_l="Price " + P + " hit the SAR dots, so it flips to long.",
               why_s="Price " + P + " hit the SAR dots, so it flips to short.",
               exit_l="SAR stop-and-reverse.", watch="Always in the market. Flips when the SAR is hit."))
    L.append(S("Ichimoku Cloud", "Trend",
               lambda d: condition(d, (d.close > d.cloud_top) & (d.tenkan > d.kijun), (d.close < d.cloud_bot) & (d.tenkan < d.kijun)),
               stop=2.0, about="Price above the cloud with Tenkan over Kijun.",
               why_l="Price " + P + " is above the cloud ({cloud_top:,.2f}) and Tenkan is over Kijun.",
               why_s="Price " + P + " is below the cloud ({cloud_bot:,.2f}) and Tenkan is under Kijun.",
               exit_l="Price left the cloud setup.", watch="Waiting for price to clear the cloud {cloud_bot:,.2f} – {cloud_top:,.2f}."))
    L.append(S("Heikin-Ashi Trend", "Trend",
               lambda d: condition(d, (d.ha_dir > 0) & (d.ha_dir.shift() > 0), (d.ha_dir < 0) & (d.ha_dir.shift() < 0)),
               stop=2.0, about="Two same-colour Heikin-Ashi candles.",
               why_l="Two green Heikin-Ashi candles in a row.", why_s="Two red Heikin-Ashi candles in a row.",
               exit_l="The Heikin-Ashi colour changed.", watch="Waiting for two same-colour Heikin-Ashi candles."))
    L.append(S("ADX + DI Trend", "Trend",
               lambda d: condition(d, (d.adx > 25) & (d.pdi > d.mdi), (d.adx > 25) & (d.mdi > d.pdi)), stop=2.0,
               about="Trades only when ADX says there is a trend.",
               why_l="ADX {adx:.0f} shows a strong trend, and buyers (+DI {pdi:.0f}) are in control.",
               why_s="ADX {adx:.0f} shows a strong trend, and sellers (−DI {mdi:.0f}) are in control.",
               exit_l="Trend strength faded (ADX under 25) or control switched.",
               watch="ADX is {adx:.0f}. Waiting for it to go above 25 (a real trend)."))
    L.append(S("Donchian Breakout (Turtle)", "Breakout",
               lambda d: enter_exit(d, d.close > d.dch20, d.close < d.dcl10, d.close < d.dcl20, d.close > d.dch10),
               stop=2.0, about="Turtle rules: 20-bar breakout, 10-bar exit.",
               why_l="Closed " + P + " at a new 20-bar high (above {dch20:,.2f}).",
               why_s="Closed " + P + " at a new 20-bar low (below {dcl20:,.2f}).",
               exit_l="Hit the 10-bar exit channel.", watch="Waiting for a 20-bar breakout: above {dch20:,.2f} or below {dcl20:,.2f}."))
    L.append(S("Keltner Channel Breakout", "Breakout",
               lambda d: enter_exit(d, d.close > d.kcu, d.close < d.ema20, d.close < d.kcl, d.close > d.ema20),
               stop=1.5, about="Closes outside the 2-ATR Keltner band, exits at the middle.",
               why_l="Closed " + P + " above the Keltner band {kcu:,.2f}.", why_s="Closed " + P + " below the Keltner band {kcl:,.2f}.",
               exit_l="Back to the middle line (20 EMA {ema20:,.2f}).",
               watch="Waiting for a close outside {kcl:,.2f} – {kcu:,.2f}."))
    L.append(S("Bollinger Squeeze Breakout", "Breakout",
               lambda d: once_per_day(d, (d.bbw_rank.shift() < 0.2) & (d.close > d.bbu), (d.bbw_rank.shift() < 0.2) & (d.close < d.bbl)),
               stop=1.5, once=True, about="Tight bands, then a close outside them.",
               why_l="The bands were squeezed tight. Price exploded up out of them to " + P + ".",
               why_s="The bands were squeezed tight. Price broke down out of them to " + P + ".",
               watch="Waiting for a squeeze (bands in their tightest 20%), then a breakout."))
    L.append(S("Bollinger Mean Reversion", "Reversal",
               lambda d: enter_exit(d, d.close < d.bbl, d.close >= d.sma20, d.close > d.bbu, d.close <= d.sma20),
               stop=1.5, about="Buys below the lower band and sells above the upper, exiting at the middle.",
               why_l="Closed " + P + " below the lower Bollinger band {bbl:,.2f}. Oversold.",
               why_s="Closed " + P + " above the upper Bollinger band {bbu:,.2f}. Overbought.",
               exit_l="Back to the middle band {sma20:,.2f}.", watch="Waiting for a close outside {bbl:,.2f} – {bbu:,.2f}."))
    L.append(S("RSI(2) Connors", "Reversal",
               lambda d: enter_exit(d, (d.rsi2 < 10) & (d.close > d.ema50), d.rsi2 > 60, (d.rsi2 > 90) & (d.close < d.ema50), d.rsi2 < 40),
               stop=1.5, about="Larry Connors: buys short-term oversold dips in an uptrend.",
               why_l="RSI(2) crashed to {rsi2:.0f} while still above the 50 EMA. A dip in an uptrend.",
               why_s="RSI(2) spiked to {rsi2:.0f} while below the 50 EMA. A pop in a downtrend.",
               exit_l="RSI(2) recovered ({rsi2:.0f}).", watch="RSI(2) is {rsi2:.0f}. It needs to drop below 10 or rise above 90."))
    L.append(S("RSI(14) 30/70 Reversal", "Reversal",
               lambda d: enter_exit(d, cross_up(d.rsi14, 30), d.rsi14 > 50, cross_dn(d.rsi14, 70), d.rsi14 < 50),
               stop=1.5, about="Classic overbought/oversold.",
               why_l="RSI(14) climbed back above 30 ({rsi14:.0f}), leaving oversold.",
               why_s="RSI(14) dropped back below 70 ({rsi14:.0f}), leaving overbought.",
               exit_l="RSI reached 50.", watch="RSI(14) is {rsi14:.0f}. Waiting for a turn from beyond 30 or 70."))
    L.append(S("Stochastic 20/80", "Reversal",
               lambda d: enter_exit(d, cross_up(d.stk, d.std_) & (d.stk < 20), d.stk > 50,
                                    cross_dn(d.stk, d.std_) & (d.stk > 80), d.stk < 50),
               stop=1.5, about="%K crossing %D at the extremes.",
               why_l="Stochastic turned up from oversold (%K {stk:.0f}).", why_s="Stochastic turned down from overbought (%K {stk:.0f}).",
               exit_l="Stochastic reached the middle.", watch="Stochastic is {stk:.0f}. Waiting for a turn below 20 or above 80."))
    L.append(S("Z-Score Stat Reversion", "Quant",
               lambda d: enter_exit(d, d.zscore < -2.5, d.zscore > -0.5, d.zscore > 2.5, d.zscore < 0.5),
               stop=2.0, about="Quant style: fades 2.5-sigma moves away from the 50-bar mean.",
               why_l="Price is {zscore:.1f} sigma below its 50-bar average. Statistically stretched.",
               why_s="Price is {zscore:.1f} sigma above its 50-bar average. Statistically stretched.",
               exit_l="Back near the average (z {zscore:.1f}).", watch="Z-score is {zscore:.1f}. It needs to go beyond ±2.5."))
    L.append(S("Signal Ensemble (5-vote)", "Quant", lambda d: _ensemble(d), stop=2.0,
               about="Majority vote of EMA, MACD, VWAP, Supertrend and the 50 EMA.",
               why_l="At least 4 of its 5 signals voted long.", why_s="At least 4 of its 5 signals voted short.",
               exit_l="The vote split.", watch="Its 5 signals disagree, so it's sitting out."))
    L.append(S("Overnight Drift", "Quant", lambda d: np.where(d.k.values >= 24, 1.0, 0.0), intraday=False,
               about="Famous anomaly: the Nasdaq gains mostly overnight. Buys late, sells after the open.",
               why_l="It's the end of the day. Buying to hold overnight, where most Nasdaq gains have historically happened.",
               exit_l="Morning: overnight hold done, cashing out after the open.",
               watch="Sleeps all day. Buys at 15:45 New York (20:45 UK)."))
    L.append(S("Time-Series Momentum (5-day)", "Quant", lambda d: _tsmom(d), intraday=False, stop=4.0,
               about="Holds the direction of the last 5 days, rebalanced near each close.",
               why_l="The last 5 days are up ({ret5d:+.2%}), so it follows the trend.",
               why_s="The last 5 days are down ({ret5d:+.2%}), so it follows the trend.",
               exit_l="The 5-day trend flipped.", watch="Decides near the close."))
    return L


# ============================================================ challenger pool (waiting to get in)
def challenger_pool():
    L = []
    L.append(S("Inside Bar Breakout", "Breakout",
               lambda d: once_per_day(d, d.inside_prev & (d.close > d.mother_h), d.inside_prev & (d.close < d.mother_l), start_k=2),
               stop=1.5, once=True, about="A quiet bar inside the one before it, then a break of the big bar.",
               why_l="After an inside bar, price broke above the mother bar's high {mother_h:,.2f}.",
               why_s="After an inside bar, price broke below the mother bar's low {mother_l:,.2f}.",
               watch="Waiting for an inside bar to form, then a breakout."))
    L.append(S("NR4 Range Expansion", "Breakout",
               lambda d: once_per_day(d, d.nr4_prev & (d.close > d.prev_h), d.nr4_prev & (d.close < d.prev_l), start_k=1),
               stop=1.5, once=True, about="Toby Crabel: the narrowest bar of the last 4 is followed by a burst.",
               why_l="The last bar was the narrowest of 4, and price burst above it to " + P + ".",
               why_s="The last bar was the narrowest of 4, and price burst below it to " + P + ".",
               watch="Waiting for a narrow-range bar, then a burst out of it."))
    L.append(S("ORB 15m + VWAP Filter", "Breakout",
               lambda d: once_per_day(d, (d.close > d.orh1) & (d.close > d.vwap), (d.close < d.orl1) & (d.close < d.vwap), start_k=1),
               stop=1.5, once=True, about="Opening-range breakout that only trades in VWAP's direction.",
               why_l="Broke the opening high {orh1:,.2f} and is above VWAP {vwap:,.2f}. Both agree.",
               why_s="Broke the opening low {orl1:,.2f} and is below VWAP {vwap:,.2f}. Both agree.",
               watch="Waiting for a breakout of {orl1:,.2f} – {orh1:,.2f} on the right side of VWAP."))
    L.append(S("Camarilla H4/L4 Breakout", "Breakout",
               lambda d: once_per_day(d, d.close > d.cam_h4, d.close < d.cam_l4), stop=1.5, once=True,
               about="Floor-trader Camarilla levels: a break of H4 or L4 starts a trend day.",
               why_l="Closed " + P + " above Camarilla H4 {cam_h4:,.2f}. Possible trend day up.",
               why_s="Closed " + P + " below Camarilla L4 {cam_l4:,.2f}. Possible trend day down.",
               watch="Breakout levels: H4 {cam_h4:,.2f} and L4 {cam_l4:,.2f}."))
    L.append(S("Camarilla H3/L3 Fade", "Reversal",
               lambda d: once_per_day(d, (d.low < d.cam_l3) & (d.close > d.cam_l3), (d.high > d.cam_h3) & (d.close < d.cam_h3)),
               stop=1.0, tp=2.0, once=True, about="Camarilla: fade the first test of H3/L3 when price closes back inside.",
               why_l="Tested Camarilla L3 {cam_l3:,.2f} and closed back above it. Fading the drop.",
               why_s="Tested Camarilla H3 {cam_h3:,.2f} and closed back below it. Fading the rally.",
               watch="Fade levels: L3 {cam_l3:,.2f} and H3 {cam_h3:,.2f}."))
    L.append(S("Pivot R1/S1 Breakout", "Breakout",
               lambda d: once_per_day(d, d.close > d.r1, d.close < d.s1), stop=1.5, once=True,
               about="Classic floor pivots: a break of R1 or S1.",
               why_l="Closed " + P + " above pivot resistance R1 {r1:,.2f}.", why_s="Closed " + P + " below pivot support S1 {s1:,.2f}.",
               watch="R1 {r1:,.2f}, S1 {s1:,.2f}."))
    L.append(S("Pivot Bounce", "Reversal",
               lambda d: once_per_day(d, (d.low <= d.s1) & (d.close > d.s1) & (d.close > d.open),
                                      (d.high >= d.r1) & (d.close < d.r1) & (d.close < d.open)),
               stop=1.0, tp=2.0, once=True, about="Buys a bounce off S1 and sells a rejection at R1.",
               why_l="Touched support S1 {s1:,.2f} and bounced with a green candle.",
               why_s="Touched resistance R1 {r1:,.2f} and got rejected with a red candle.",
               watch="Watching S1 {s1:,.2f} and R1 {r1:,.2f} for a bounce."))
    L.append(S("Donchian 55 (Turtle 2)", "Breakout",
               lambda d: enter_exit(d, d.close > d.dch55, d.close < d.dcl20, d.close < d.dcl55, d.close > d.dch20),
               stop=2.0, intraday=False, about="Turtle System 2: 55-bar breakout, 20-bar exit, can hold overnight.",
               why_l="New 55-bar high: " + P + " above {dch55:,.2f}.", why_s="New 55-bar low: " + P + " below {dcl55:,.2f}.",
               exit_l="Hit the 20-bar exit channel.", watch="Waiting for a 55-bar breakout: above {dch55:,.2f} or below {dcl55:,.2f}."))
    L.append(S("Williams %R Reversal", "Reversal",
               lambda d: enter_exit(d, cross_up(d.willr, -80), d.willr > -50, cross_dn(d.willr, -20), d.willr < -50),
               stop=1.5, about="Larry Williams' %R leaving the extreme zones.",
               why_l="%R climbed out of oversold ({willr:.0f}).", why_s="%R dropped out of overbought ({willr:.0f}).",
               exit_l="%R reached the middle.", watch="%R is {willr:.0f}. Waiting for a turn beyond −80 or −20."))
    L.append(S("CCI ±100 Reversal", "Reversal",
               lambda d: enter_exit(d, cross_up(d.cci, -100), d.cci > 0, cross_dn(d.cci, 100), d.cci < 0),
               stop=1.5, about="Commodity Channel Index turning back from extremes.",
               why_l="CCI turned up through −100 ({cci:.0f}).", why_s="CCI turned down through +100 ({cci:.0f}).",
               exit_l="CCI back at zero.", watch="CCI is {cci:.0f}. Waiting for a turn beyond ±100."))
    L.append(S("MFI 20/80 Reversal", "Reversal",
               lambda d: enter_exit(d, cross_up(d.mfi, 20), d.mfi > 50, cross_dn(d.mfi, 80), d.mfi < 50),
               stop=1.5, about="Money Flow Index: a volume-weighted RSI.",
               why_l="Money flow turned up from oversold (MFI {mfi:.0f}).", why_s="Money flow turned down from overbought (MFI {mfi:.0f}).",
               exit_l="MFI reached 50.", watch="MFI is {mfi:.0f}. Waiting for a turn beyond 20 or 80."))
    L.append(S("Three Bar Pullback", "Reversal",
               lambda d: enter_exit(d, d.down3 & (d.close > d.ema50), d.close > d.ema5, d.up3 & (d.close < d.ema50), d.close < d.ema5),
               stop=1.5, about="Three lower closes in an uptrend, then buy the dip (and the reverse).",
               why_l="Three lower closes in a row, but still above the 50 EMA. Buying the dip.",
               why_s="Three higher closes in a row, but still below the 50 EMA. Selling the pop.",
               exit_l="Price got back over the 5 EMA.", watch="Waiting for 3 bars in a row against the trend."))
    L.append(S("Keltner Fade", "Reversal",
               lambda d: enter_exit(d, d.close < d.kcl, d.close >= d.ema20, d.close > d.kcu, d.close <= d.ema20),
               stop=1.5, about="The opposite of the Keltner breakout: fades closes outside the band.",
               why_l="Closed " + P + " below the Keltner band {kcl:,.2f}. Fading the overextension.",
               why_s="Closed " + P + " above the Keltner band {kcu:,.2f}. Fading the overextension.",
               exit_l="Back at the 20 EMA.", watch="Waiting for a close outside {kcl:,.2f} – {kcu:,.2f}."))
    L.append(S("Pin Bar at VWAP Band", "Reversal",
               lambda d: once_per_day(d, d.pin_bull & (d.low < d.vwap - d.vwap_sd), d.pin_bear & (d.high > d.vwap + d.vwap_sd), start_k=1),
               stop=1.0, tp=2.0, once=True, about="Price-action reversal: a long-wick candle below or above the VWAP band.",
               why_l="Hammer candle (long lower wick to {low:,.2f}) below the VWAP band. Buyers rejected the low.",
               why_s="Shooting-star candle (long upper wick to {high:,.2f}) above the VWAP band. Sellers rejected the high.",
               watch="Waiting for a long-wick rejection candle away from VWAP."))
    L.append(S("Engulfing Reversal", "Reversal",
               lambda d: enter_exit(d, d.engulf_bull & (d.rsi14 < 40), d.rsi14 > 55, d.engulf_bear & (d.rsi14 > 60), d.rsi14 < 45),
               stop=1.0, about="A candle that swallows the previous one, at oversold or overbought RSI.",
               why_l="Bullish engulfing candle with RSI at {rsi14:.0f}.", why_s="Bearish engulfing candle with RSI at {rsi14:.0f}.",
               exit_l="RSI recovered.", watch="Waiting for an engulfing candle at an extreme."))
    L.append(S("Hull MA Trend", "Trend", lambda d: condition(d, d.hma_slope > 0, d.hma_slope < 0), stop=2.0,
               about="Hull moving average: a fast, smooth trend line. Follows its slope.",
               why_l="The Hull MA turned up ({hma:,.2f}).", why_s="The Hull MA turned down ({hma:,.2f}).",
               exit_l="The Hull MA turned.", watch="Waiting for the Hull MA to turn."))
    L.append(S("KAMA Adaptive Trend", "Trend",
               lambda d: condition(d, (d.close > d.kama) & (d.kama_slope > 0), (d.close < d.kama) & (d.kama_slope < 0)), stop=2.0,
               about="Kaufman's adaptive average: speeds up in trends, slows down in chop.",
               why_l="Price " + P + " is above a rising KAMA ({kama:,.2f}).", why_s="Price " + P + " is below a falling KAMA ({kama:,.2f}).",
               exit_l="KAMA trend lost.", watch="KAMA {kama:,.2f}. Waiting for price and slope to agree."))
    L.append(S("Aroon Trend", "Trend",
               lambda d: condition(d, (d.aroon_up > 70) & (d.aroon_up > d.aroon_dn), (d.aroon_dn > 70) & (d.aroon_dn > d.aroon_up)),
               stop=2.0, about="Aroon: how recently the 25-bar high or low was made.",
               why_l="Aroon Up {aroon_up:.0f}: fresh highs keep coming.", why_s="Aroon Down {aroon_dn:.0f}: fresh lows keep coming.",
               exit_l="Aroon lost its edge.", watch="Aroon Up {aroon_up:.0f} / Down {aroon_dn:.0f}. Needs one above 70."))
    L.append(S("Chandelier Exit Trend", "Trend", lambda d: condition(d, d.ch_dir > 0, d.ch_dir < 0),
               about="Chuck LeBeau's chandelier: rides a trend until it's 3 ATR off the extreme.",
               why_l="Price " + P + " broke above the short-side chandelier ({ch_short:,.2f}).",
               why_s="Price " + P + " broke below the long-side chandelier ({ch_long:,.2f}).",
               exit_l="Chandelier flipped.", watch="Waiting for a chandelier flip."))
    L.append(S("Elder Impulse", "Trend", lambda d: condition(d, d.impulse > 0, d.impulse < 0), stop=1.5,
               about="Alexander Elder: the 13 EMA and MACD histogram must both point the same way.",
               why_l="Impulse is green: the 13 EMA is rising and MACD momentum is rising.",
               why_s="Impulse is red: the 13 EMA is falling and MACD momentum is falling.",
               exit_l="Impulse went neutral.", watch="Impulse is neutral. Waiting for green or red."))
    L.append(S("Linear Regression Slope", "Trend",
               lambda d: condition(d, d.lr_slope > 0.15 * d.atr / 5, d.lr_slope < -0.15 * d.atr / 5), stop=2.0,
               about="Fits a straight line through the last 20 bars and trades its slope.",
               why_l="The 20-bar regression line slopes up ({lr_slope:+.2f} pts per bar).",
               why_s="The 20-bar regression line slopes down ({lr_slope:+.2f} pts per bar).",
               exit_l="The slope flattened.", watch="Slope {lr_slope:+.2f} pts per bar. Too flat to trade."))
    L.append(S("Vortex Indicator", "Trend",
               lambda d: condition(d, (d.vi_p > d.vi_m) & (d.vi_p > 1.05), (d.vi_m > d.vi_p) & (d.vi_m > 1.05)), stop=2.0,
               about="Vortex: compares upward and downward price movement.",
               why_l="Upward vortex ({vi_p:.2f}) is beating downward ({vi_m:.2f}).",
               why_s="Downward vortex ({vi_m:.2f}) is beating upward ({vi_p:.2f}).",
               exit_l="Vortex lost its edge.", watch="VI+ {vi_p:.2f} / VI− {vi_m:.2f}. Waiting for a clear leader."))
    L.append(S("TRIX Signal Cross", "Trend", lambda d: condition(d, d.trix > d.trix_s, d.trix < d.trix_s), stop=2.0,
               about="Triple-smoothed momentum crossing its signal line.",
               why_l="TRIX crossed above its signal line.", why_s="TRIX crossed below its signal line.",
               exit_l="TRIX crossed back.", watch="Waiting for a TRIX cross."))
    L.append(S("Triple EMA Stack 5/13/50", "Trend",
               lambda d: condition(d, (d.ema5 > d.ema13) & (d.ema13 > d.ema50), (d.ema5 < d.ema13) & (d.ema13 < d.ema50)), stop=2.0,
               about="Only trades when the 5, 13 and 50 EMAs are all stacked the same way.",
               why_l="EMAs stacked bullish: 5 > 13 > 50.", why_s="EMAs stacked bearish: 5 < 13 < 50.",
               exit_l="The EMA stack broke.", watch="The EMAs aren't lined up. Sitting out."))
    L.append(S("Midday VWAP Reversion", "Quant",
               lambda d: enter_exit(d, (d.k >= 10) & (d.k <= 18) & (d.close < d.vwap - 1.5 * d.vwap_sd), d.close >= d.vwap,
                                    (d.k >= 10) & (d.k <= 18) & (d.close > d.vwap + 1.5 * d.vwap_sd), d.close <= d.vwap, last_entry_k=18),
               stop=1.5, about="The quiet lunch hours tend to drift back to VWAP. Fades stretches from 12:00 to 14:00 NY.",
               why_l="Lunchtime stretch: " + P + " is 1.5 SD under VWAP {vwap:,.2f}.",
               why_s="Lunchtime stretch: " + P + " is 1.5 SD over VWAP {vwap:,.2f}.",
               exit_l="Back at VWAP.", watch="Active 12:00-14:00 New York (17:00-19:00 UK)."))
    L.append(S("Afternoon Trend Continuation", "Quant",
               lambda d: once_per_day(d, (d.k == 13) & (d.am_ret > 0.003), (d.k == 13) & (d.am_ret < -0.003), start_k=13, last_entry_k=13),
               stop=1.5, once=True, about="If the morning moved strongly, holds that direction into the close.",
               why_l="The morning gained {am_ret:+.2%}. Holding the trend into the close.",
               why_s="The morning lost {am_ret:+.2%}. Holding the trend into the close.",
               watch="Decides at 12:45 New York (17:45 UK)."))
    L.append(S("Volume Spike Momentum", "Momentum",
               lambda d: enter_exit(d, (d.vol_ratio > 2) & (d.close > d.open) & (d.close > d.vwap), d.close < d.ema9,
                                    (d.vol_ratio > 2) & (d.close < d.open) & (d.close < d.vwap), d.close > d.ema9),
               stop=1.5, about="Follows a bar with more than double the normal volume.",
               why_l="Volume spike ({vol_ratio:.1f}x normal) on a green bar above VWAP. Big buyers stepped in.",
               why_s="Volume spike ({vol_ratio:.1f}x normal) on a red bar below VWAP. Big sellers stepped in.",
               exit_l="Momentum faded under the 9 EMA.", watch="Waiting for a volume spike (2x normal)."))
    L.append(S("Range Expansion Bar", "Momentum",
               lambda d: once_per_day(d, (d.range_atr > 2) & (d.close > d.open), (d.range_atr > 2) & (d.close < d.open), start_k=1),
               stop=1.5, once=True, about="A bar twice the normal size usually starts a move. Follows it.",
               why_l="A huge green bar ({range_atr:.1f}x ATR). Following the thrust.",
               why_s="A huge red bar ({range_atr:.1f}x ATR). Following the thrust.",
               watch="Waiting for a bar twice the normal size."))
    L.append(S("Yesterday's Loser Bounce", "Quant",
               lambda d: once_per_day(d, (d.k == 0) & (d.pdret < -0.01), (d.k == 0) & (d.pdret > 0.015), last_entry_k=0),
               stop=2.0, once=True, about="Short-term reversal: after a big down day, buys the next day.",
               why_l="Yesterday fell {pdret:+.2%}. Betting on a bounce.",
               why_s="Yesterday ripped {pdret:+.2%}. Betting on a pullback.",
               watch="Only trades after a big move yesterday."))
    L.append(S("Overnight Drift + Trend Filter", "Quant",
               lambda d: np.where((d.k.values >= 24) & (d.close.values > d.ema50.values), 1.0, 0.0), intraday=False,
               about="The overnight anomaly, but only when price is above the 50 EMA.",
               why_l="End of day, and the trend is up (above the 50 EMA {ema50:,.2f}). Holding overnight.",
               exit_l="Morning: overnight hold done.", watch="Buys at 15:45 New York if the trend is up."))
    L.append(S("Oscillator Ensemble", "Quant", lambda d: _osc_ensemble(d), stop=1.5,
               about="Votes from RSI, Stochastic, Williams %R, CCI and MFI. Buys when most say oversold.",
               why_l="Most oscillators agree it's oversold.", why_s="Most oscillators agree it's overbought.",
               exit_l="The oscillators calmed down.", watch="The oscillators are neutral."))
    L.append(S("Turnaround Tuesday", "Quant",
               lambda d: once_per_day(d, (d.k == 0) & (d.dow == 1) & (d.pdret < 0), np.zeros(len(d), bool), last_entry_k=0),
               stop=2.0, once=True, about="A famous calendar effect: if Monday fell, buy Tuesday.",
               why_l="It's Tuesday and Monday fell ({pdret:+.2%}). Turnaround time.",
               watch="Only trades on Tuesdays after a down Monday."))
    return L


def _last_half_hour(d):
    k = d["k"].values
    sig = np.sign(np.nan_to_num(d["first30"].values))
    t = np.zeros(len(d))
    hold = k >= 23
    t[hold] = sig[hold]
    return t


def _ensemble(d):
    votes = ((d.ema9 > d.ema21).astype(int) + (d.macd > d.macds).astype(int) + (d.close > d.vwap).astype(int)
             + (d.st_dir > 0).astype(int) + (d.close > d.ema50).astype(int))
    return condition(d, votes >= 4, votes <= 1)


def _osc_ensemble(d):
    os_ = ((d.rsi14 < 35).astype(int) + (d.stk < 20).astype(int) + (d.willr < -80).astype(int)
           + (d.cci < -100).astype(int) + (d.mfi < 25).astype(int))
    ob_ = ((d.rsi14 > 65).astype(int) + (d.stk > 80).astype(int) + (d.willr > -20).astype(int)
           + (d.cci > 100).astype(int) + (d.mfi > 75).astype(int))
    return enter_exit(d, os_ >= 3, os_ == 0, ob_ >= 3, ob_ == 0)


def _tsmom(d):
    k = d["k"].values
    r = d["ret5d"].values
    t = np.zeros(len(d))
    cur = 0.0
    for i in range(len(d)):
        if k[i] == 24 and not np.isnan(r[i]):
            cur = float(np.sign(r[i]))
        t[i] = cur
    return t


def benchmark():
    return S("Buy & Hold", "Benchmark", lambda d: np.ones(len(d)), intraday=False,
             about="Just holds 1 contract the whole time. Every fighter should beat this.",
             why_l="Always long.", watch="Always long.")


# ============================================================ the Monkey team (luck test)
def _mix(x):
    """Deterministic pseudo-random numbers from integers (same bar + same monkey = same 'coin flip' every run)."""
    x = x.astype(np.uint64)
    x ^= x >> np.uint64(33)
    x *= np.uint64(0xFF51AFD7ED558CCD)
    x ^= x >> np.uint64(33)
    x *= np.uint64(0xC4CEB9FE1A85EC53)
    x ^= x >> np.uint64(33)
    return (x >> np.uint64(11)).astype(np.float64) / float(2 ** 53)


def monkeys(n=20, trades_per_day=2.0, intraday=True):
    """Random traders: at any bar they may flip a coin, go long or short, and hold for 30 min to 4 hours.
    A strategy that can't beat most of them is probably just lucky."""
    import zlib
    out = []
    for k in range(n):
        def fn(d, k=k):
            bpd = d.attrs.get("bpd", 26)
            asset = str(d["asset"].iloc[0]) if "asset" in d else ""
            slot = np.asarray(d.index.tz_convert("UTC").as_unit("ns").asi8 // 900_000_000_000, dtype=np.int64)
            salt = (zlib.crc32(f"{asset}|{k}".encode()) + 1) * 2654435761
            base = (slot.astype(np.uint64) * np.uint64(6364136223846793005)) + np.uint64(salt % (2 ** 63))
            u1, u2, u3 = _mix(base), _mix(base + np.uint64(1)), _mix(base + np.uint64(2))
            p = trades_per_day / bpd
            t = np.zeros(len(d))
            cur, left = 0, 0
            kk = d["k"].values
            for i in range(len(d)):
                if kk[i] == 0 and intraday:
                    cur, left = 0, 0
                if left > 0:
                    left -= 1
                    if left == 0:
                        cur = 0
                if cur == 0 and u1[i] < p:
                    cur = 1 if u2[i] < 0.5 else -1
                    left = 2 + int(u3[i] * 15)
                t[i] = cur
            return t
        out.append(S(f"Monkey #{k + 1}", "Monkey", fn, intraday=intraday, about="Trades at random.",
                     why_l="Flipped a coin: heads, buy.", why_s="Flipped a coin: tails, sell.", scope="each"))
    return out
