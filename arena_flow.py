# ===================== STRATEGY ARENA — NASDAQ TOWER v2: hourly winners + order-flow fighters =====================
# 1) The 3 strategies that survived the 2-year prop test (NR4, Chandelier, Overnight Drift + Trend Filter) run on
#    1-HOUR candles, exactly like in that test. Their hourly decisions are placed on the tower's 15-minute timeline
#    at the moment each hour closes, so they fill at the next hour's open, just like in the backtest.
# 2) Two order-flow fighters built from a trader's "value area" method, on 15-MINUTE candles. Each candle's own
#    volume profile (value area = where ~70% of the volume traded, POC = busiest price) is rebuilt from that
#    candle's fifteen 1-minute bars. Yahoo has no real buy/sell (tick) data, so "delta" is estimated from where each
#    1-minute bar closed inside its range. "NASDAQ Effort" is private, so a stand-in is used: the last 3 candles'
#    delta added up. Stops and targets are checked minute by minute.
# Decisions only use finished candles. Paper money only.
import os
import numpy as np
import pandas as pd
import arena_core as C
from arena_strats import S

NY = "America/New_York"
BIN = 1.0           # volume-profile bucket, in index points
VA_SHARE = 0.70     # value area = 70% of the volume
TICK = 0.25
_H1 = {}            # id(15-min frame) -> (hourly frame, decision positions)


# ---------------------------------------------------------------- 1-minute bars
def load_1m(folder, sym="NQ=F", keep_days=45):
    """Keeps a growing file of 1-minute bars (Yahoo only serves the last 7 days of 1-minute data)."""
    path = os.path.join(folder, "bars_NQ_F_1m.csv") if folder else None
    old = None
    if path and os.path.exists(path):
        old = pd.read_csv(path, index_col=0)
        old.index = pd.to_datetime(old.index, utc=True)
    new = None
    try:
        import yfinance as yf
        x = yf.download(sym, period="7d", interval="1m", prepost=True, auto_adjust=False, progress=False)
        if isinstance(x.columns, pd.MultiIndex):
            lv = [i for i in range(x.columns.nlevels) if "Close" in x.columns.get_level_values(i)]
            x.columns = x.columns.get_level_values(lv[0] if lv else 0)
        x = x.loc[:, ~x.columns.duplicated()]
        new = x[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
        new.index = pd.to_datetime(new.index, utc=True)
    except Exception as e:
        print(f"1-minute download skipped ({e}).")
    parts = [p for p in (old, new) if p is not None and len(p)]
    if not parts:
        return None
    allb = pd.concat(parts)
    allb = allb[~allb.index.duplicated(keep="last")].sort_index()
    allb = allb[allb.index >= allb.index.max() - pd.Timedelta(days=keep_days)]
    if path:
        allb.to_csv(path)
    return allb


def _profile(lo, hi, vol):
    """Spreads each 1-minute bar's volume evenly over the price buckets it traded through."""
    b0 = int(np.floor(lo.min() / BIN))
    b1 = int(np.floor(hi.max() / BIN))
    hist = np.zeros(b1 - b0 + 1)
    for l_, h_, v_ in zip(lo, hi, vol):
        a, b = int(np.floor(l_ / BIN)) - b0, int(np.floor(h_ / BIN)) - b0
        hist[a:b + 1] += v_ / (b - a + 1)
    return b0, hist


def _value_area(b0, hist):
    """POC = busiest bucket; grow from it toward the busier side until 70% of the volume is inside."""
    tot = hist.sum()
    if tot <= 0:
        mid = (b0 + len(hist) / 2) * BIN
        return mid, mid, mid
    p = int(np.argmax(hist))
    lo = hi = p
    inside = hist[p]
    while inside < VA_SHARE * tot and (lo > 0 or hi < len(hist) - 1):
        up = hist[hi + 1] if hi < len(hist) - 1 else -1
        dn = hist[lo - 1] if lo > 0 else -1
        if up >= dn:
            hi += 1
            inside += up
        else:
            lo -= 1
            inside += dn
    return (b0 + lo) * BIN, (b0 + hi + 1) * BIN, (b0 + p + 0.5) * BIN


def add_flow_cols(d, m1):
    """Per 15-min candle: value area low/high, POC, estimated delta, its own 1-min volume; plus the session's
    developing value area. Prices are aligned to the (roll-adjusted) 15-min chart."""
    n = len(d)
    cols = {k: np.full(n, np.nan) for k in ("va_lo", "va_hi", "poc", "cdelta", "cvol", "s_val", "s_vah", "s_poc")}
    d.attrs.pop("m1", None)
    _M1[id(d)] = None
    if m1 is not None and len(m1):
        x = m1.copy()
        x.index = x.index.tz_convert(NY)
        x = x[x.High >= x.Low]
        key = x.index.floor("15min")
        pos = d.index.get_indexer(pd.DatetimeIndex(key).unique())
        offs = np.full(n, np.nan)
        dates = d["date"].values
        sess, s_b0, s_hist = None, None, None
        groups = dict(list(x.groupby(key)))
        cl15 = d["close"].values
        for i in range(n):
            g = groups.get(d.index[i])
            if dates[i] != sess:
                sess, s_b0, s_hist = dates[i], None, None
            if g is None or len(g) < 5:
                continue
            off = cl15[i] - float(g.Close.values[-1])
            offs[i] = off
            lo, hi, v = g.Low.values + off, g.High.values + off, g.Volume.values.astype(float)
            o_, c_ = g.Open.values + off, g.Close.values + off
            rng = hi - lo
            clv = np.where(rng > 0, (2 * c_ - hi - lo) / np.where(rng > 0, rng, 1), np.sign(c_ - o_))
            cols["cdelta"][i] = float((v * clv).sum())
            cols["cvol"][i] = float(v.sum())
            b0, hist = _profile(lo, hi, v)
            cols["va_lo"][i], cols["va_hi"][i], cols["poc"][i] = _value_area(b0, hist)
            # session profile so far (18:00 New York to this candle)
            if s_hist is None:
                s_b0, s_hist = b0, hist.copy()
            else:
                nb0 = min(s_b0, b0)
                nb1 = max(s_b0 + len(s_hist), b0 + len(hist))
                h2 = np.zeros(nb1 - nb0)
                h2[s_b0 - nb0:s_b0 - nb0 + len(s_hist)] += s_hist
                h2[b0 - nb0:b0 - nb0 + len(hist)] += hist
                s_b0, s_hist = nb0, h2
            cols["s_val"][i], cols["s_vah"][i], cols["s_poc"][i] = _value_area(s_b0, s_hist)
        _M1[id(d)] = (x, offs)
    for k, v in cols.items():
        d[k] = v
    # value-area direction: is this candle's value area higher (+1) or lower (-1) than the previous candle's?
    mid = (d.va_lo + d.va_hi) / 2
    same = d["date"].values == np.roll(d["date"].values, 1)
    raw = np.sign(mid.diff()).values.copy()
    raw[~same] = 0
    raw[np.isnan(raw)] = 0
    dirn = np.zeros(n)
    for i in range(n):
        dirn[i] = raw[i] if raw[i] != 0 else (dirn[i - 1] if (i > 0 and same[i] and not np.isnan(mid.values[i])) else 0)
    d["va_dir"] = dirn
    prev = np.roll(dirn, 1)
    prev[~same] = 0
    d["va_prev_dir"] = prev
    d["effort"] = pd.Series(d.cdelta).rolling(3, min_periods=3).sum()
    avgv = pd.Series(d.cvol).rolling(20, min_periods=8).mean()
    body = (d.close - d.open).abs()
    rng = (d.high - d.low).replace(0, np.nan)
    d["absorb"] = (d.cvol >= 1.3 * avgv) & (body <= 0.35 * rng)            # lots of effort, little result
    d["absorb_sell"] = d.absorb & (d.cdelta < 0)
    d["absorb_buy"] = d.absorb & (d.cdelta > 0)
    return d


_M1 = {}


# ---------------------------------------------------------------- engine for the order-flow fighters
def _path(d, i):
    """The 1-minute bars inside 15-min candle i (aligned prices), or None."""
    got = _M1.get(id(d))
    if not got:
        return None
    x, offs = got
    if np.isnan(offs[i]):
        return None
    t0 = d.index[i]
    g = x.loc[t0:t0 + pd.Timedelta(minutes=14)]
    if not len(g):
        return None
    off = offs[i]
    return np.c_[g.Open.values + off, g.High.values + off, g.Low.values + off, g.Close.values + off]


def flow_engine(d, strat, point_value=20.0, cost_rt=14.0, contracts=1, notional=None, cost_pct=None, asset=""):
    """plan(d) gives, per candle, an entry signal (+1/-1), whether it is a fresh setup, its stop price,
    its reward:risk (target) and the trade-management style. Entries fill at the next candle's open;
    stops/targets are checked on 1-minute bars (stop first if a minute touches both)."""
    sig, fresh, stop_px, rr = strat["plan"](d)
    style = strat.get("style", "scalp")
    o, h, l, c = (d[x].values for x in ("open", "high", "low", "close"))
    last, k = d["last"].values, d["k"].values
    cd = d["cdelta"].values
    idx, n = d.index, len(d)
    units = point_value * contracts
    cost = cost_rt * contracts
    trades, eq = [], np.zeros(n)
    realized = 0.0
    st = None
    blocked = 0
    last_win_side = 0
    for i in range(1, n):
        j = i - 1                                               # decision candle
        new_sess = d["date"].values[i] != d["date"].values[j]
        if new_sess:
            blocked, last_win_side = 0, 0
        s = int(sig[j]) if not last[j] else 0
        if fresh[j] != 0 and blocked == fresh[j]:
            blocked = 0
        # opposite fresh setup while in a trade: get out and turn around
        if st and s == -st["side"] and fresh[j] == s:
            px = o[i]
            pnl = (px - st["entry"]) * st["side"] * units - cost
            trades.append((asset, st["e"], i, st["side"], st["entry"], px, pnl, "flip", st["e"] - 1, j, st["stop0"], st["tp"]))
            realized += pnl
            st = None
        if st is None and s != 0 and not new_sess:
            ok_fresh = fresh[j] == s
            ok_again = (s == last_win_side) and style == "scalp"         # re-entry after a win, same direction
            if (ok_fresh or ok_again) and blocked != s:
                ent = o[i]
                sp = stop_px[j]
                risk = (ent - sp) * s
                if risk > TICK * 2 and np.isfinite(sp):
                    tp = ent + s * rr[j] * risk if style == "scalp" else None
                    st = dict(side=s, entry=ent, e=i, stop=sp, stop0=sp, tp=tp, conf=0)
                    last_win_side = 0
        if st:
            p = st["side"]
            path = _path(d, i)
            if path is None:
                path = np.array([[o[i], h[i], l[i], c[i]]])
            done = None
            for (mo, mh, ml, mc) in path:
                hit_s = (p > 0 and ml <= st["stop"]) or (p < 0 and mh >= st["stop"])
                hit_t = st["tp"] is not None and ((p > 0 and mh >= st["tp"]) or (p < 0 and ml <= st["tp"]))
                if hit_s:
                    px = min(mo, st["stop"]) if p > 0 else max(mo, st["stop"])
                    why = "stop" if (st["stop"] - st["entry"]) * p < 0 else ("breakeven" if st["stop"] == st["entry"] else "trail")
                    done = (px, why)
                    break
                if hit_t:
                    done = (max(mo, st["tp"]) if p > 0 else min(mo, st["tp"]), "target")
                    break
            if done is None and last[i]:
                done = (c[i], "close")
            if done:
                px, why = done
                pnl = (px - st["entry"]) * p * units - cost
                trades.append((asset, st["e"], i, p, st["entry"], px, pnl, why, st["e"] - 1, i, st["stop0"], st["tp"]))
                realized += pnl
                if why == "target":
                    last_win_side = p
                elif why == "stop":
                    blocked, last_win_side = p, 0
                st = None
            elif style == "trend":
                # management decided at this candle's close, used from the next candle on
                green = (c[i] - o[i]) * p > 0 and cd[i] * p > 0
                if green:
                    st["conf"] += 1
                if st["conf"] >= 1:
                    st["stop"] = max(st["stop"], st["entry"]) if p > 0 else min(st["stop"], st["entry"])      # breakeven
                if st["conf"] >= 2 and i - 1 > st["e"]:
                    ref = l[i - 1] - TICK if p > 0 else h[i - 1] + TICK                                      # trail behind the second-to-last candle
                    st["stop"] = max(st["stop"], ref) if p > 0 else min(st["stop"], ref)
        eq[i] = realized + ((c[i] - st["entry"]) * st["side"] * units if st else 0.0)
    cols = ["asset", "entry_i", "exit_i", "side", "entry", "exit", "pnl", "exit_reason", "in_dec", "out_dec", "stop", "target"]
    tr = pd.DataFrame(trades, columns=cols)
    tr["entry_time"] = idx[tr.entry_i.values.astype(int)] if len(tr) else pd.DatetimeIndex([], tz=idx.tz)
    tr["exit_time"] = idx[tr.exit_i.values.astype(int)] if len(tr) else pd.DatetimeIndex([], tz=idx.tz)
    if len(tr):
        tr.loc[tr.exit_reason == "close", "exit_time"] = tr.loc[tr.exit_reason == "close", "exit_time"] + pd.Timedelta(minutes=15)
    tr.attrs["equity"] = pd.Series(eq, index=idx)
    tr.attrs["open"] = []
    if st:
        tr.attrs["open"] = [dict(asset=asset, side=st["side"], entry=st["entry"], entry_time=idx[st["e"]], stop=st["stop"],
                                 target=st["tp"], in_dec=st["e"] - 1, upnl=(c[n - 1] - st["entry"]) * st["side"] * units)]
    return tr


# ---------------------------------------------------------------- the two order-flow fighters
def _window(d):
    k = d["k"].values
    return (k >= 1) & (k <= 87)            # no new trades in the first candle (18:00) or after 15:45 New York


def plan_machine_gun(d):
    up = (d.va_dir == 1).values
    dn = (d.va_dir == -1).values
    flip_up = up & (d.va_prev_dir == -1).values
    flip_dn = dn & (d.va_prev_dir == 1).values
    green = (d.close > d.open).values & (d.cdelta > 0).values
    red = (d.close < d.open).values & (d.cdelta < 0).values
    eff_up, eff_dn = (d.effort > 0).values, (d.effort < 0).values
    w = _window(d)
    L = up & green & eff_up & w
    Sh = dn & red & eff_dn & w
    sig = np.where(L, 1, np.where(Sh, -1, 0))
    fresh = np.where(L & flip_up, 1, np.where(Sh & flip_dn, -1, 0))
    stop = np.where(sig > 0, d.va_lo.values - TICK, np.where(sig < 0, d.va_hi.values + TICK, np.nan))
    absorbed = np.where(sig > 0, d.absorb_sell.values, d.absorb_buy.values)
    rr = np.where(absorbed, 2.0, 1.0)
    return sig, fresh, stop, rr


def plan_trend_rider(d, report=False):
    a = d.atr.values
    out_up = (d.close > d.s_vah).values
    out_dn = (d.close < d.s_val).values
    lvl_l = np.fmax(d.vwap.values, d.s_vah.values)
    lvl_s = np.fmin(d.vwap.values, d.s_val.values)
    touch_l = d.low.values <= lvl_l + 0.25 * a
    touch_s = d.high.values >= lvl_s - 0.25 * a
    # absorption = the other side hit hard but price didn't follow: selling delta on a candle that didn't fall,
    # or a big-volume small-body candle with selling delta (mirror for shorts). Looked for in this or the 2 previous candles.
    sell_abs = (d.absorb_sell | ((d.cdelta < 0) & (d.close >= d.open))).values
    buy_abs = (d.absorb_buy | ((d.cdelta > 0) & (d.close <= d.open))).values
    ab_s = sell_abs | np.roll(sell_abs, 1) | np.roll(sell_abs, 2)
    ab_b = buy_abs | np.roll(buy_abs, 1) | np.roll(buy_abs, 2)
    green = (d.close > d.open).values & (d.cdelta > 0).values
    red = (d.close < d.open).values & (d.cdelta < 0).values
    w = _window(d)
    L = out_up & touch_l & ab_s & green & w
    Sh = out_dn & touch_s & ab_b & red & w
    if report:
        has = d.cdelta.notna().values
        print("VA Trend Rider check (candles with 1-min data):", int(has.sum()),
              "| outside value area up/down:", int((out_up & has).sum()), int((out_dn & has).sum()),
              "| + at a level:", int((out_up & touch_l).sum()), int((out_dn & touch_s).sum()),
              "| + absorption:", int((out_up & touch_l & ab_s).sum()), int((out_dn & touch_s & ab_b).sum()),
              "| + delta candle (signals):", int(L.sum()), int(Sh.sum()))
    sig = np.where(L, 1, np.where(Sh, -1, 0))
    stop = np.where(sig > 0, np.fmin(d.low.values, lvl_l) - TICK, np.where(sig < 0, np.fmax(d.high.values, lvl_s) + TICK, np.nan))
    return sig, sig.copy(), stop, np.ones(len(d))


def flow_roster():
    mg = S("VA Machine Gun (1:1)", "OrderFlow", None,
           about="1:1 scalps from each 15-min candle's own volume profile: trades the moment the value area flips "
                 "direction on a candle of the same colour with buyers (or sellers) in control.",
           why_l="This candle's value area ({va_lo:,.2f}–{va_hi:,.2f}) moved HIGHER, the candle closed green with buying delta "
                 "({cdelta:+,.0f}) and the 3-candle pressure agrees ({effort:+,.0f}). Stop under the value-area low, 1:1 target.",
           why_s="This candle's value area ({va_lo:,.2f}–{va_hi:,.2f}) moved LOWER, the candle closed red with selling delta "
                 "({cdelta:+,.0f}) and the 3-candle pressure agrees ({effort:+,.0f}). Stop over the value-area high, 1:1 target.",
           exit_l="Hit its 1:1 target or its stop.",
           watch="Waiting for the 15-min value area to flip direction on a candle that agrees (colour + delta + pressure).")
    mg.update(engine=flow_engine, plan=plan_machine_gun, style="scalp", rules=[
        "Every 15-min candle gets its own volume profile from its 1-minute bars: value area (70% of the volume) and POC.",
        "LONG: the value area flips from moving lower to moving higher, the candle closes green, delta is positive and the "
        "3-candle pressure (stand-in for 'NASDAQ Effort') is positive. SHORT: the mirror image.",
        "Skips the trade if the value area flips one way but the candle closes the other colour.",
        "Stop: just below the signal candle's value-area low (long) / above its value-area high (short).",
        "Target: 1:1. Goes for 1:2 only when the candle shows heavy absorption (big volume, small body, the other side hitting).",
        "After a winning trade, the next candle that keeps the value area moving the same way is another 1:1 entry. "
        "After a stop, waits for a brand-new flip.",
        "Enters at the next candle's open; stops and targets are checked minute by minute. Flat by 16:45 New York.",
        "Delta is estimated from 1-minute bars (Yahoo has no real tick data), so this is an approximation of the method."])
    tr = S("VA Trend Rider", "OrderFlow", None,
           about="Bigger intraday moves: only trades when price has left the session's value area ('out of the cage'), "
                 "after absorption at a key level and a delta candle in its direction. Breakeven, then trails.",
           why_l="Price is above the session value area ({s_val:,.2f}–{s_vah:,.2f}), pulled back to VWAP/value-area high, "
                 "sellers got absorbed and this candle closed green with buying delta ({cdelta:+,.0f}).",
           why_s="Price is below the session value area ({s_val:,.2f}–{s_vah:,.2f}), bounced into VWAP/value-area low, "
                 "buyers got absorbed and this candle closed red with selling delta ({cdelta:+,.0f}).",
           exit_l="Trailing stop, breakeven stop or the 16:45 New York flat.",
           watch="Waiting for price to leave the session value area, then absorption + a delta candle at a level.")
    tr.update(engine=flow_engine, plan=plan_trend_rider, style="trend", rules=[
        "Only trades when price is OUTSIDE the session's value area (inside it, buyers and sellers are balanced: 'the cage').",
        "Entry level: VWAP or the session value-area high/low. Confirmation: absorption on the other side in this or the "
        "previous candle (big volume, small body), then a delta candle in its direction.",
        "Stop: just beyond the signal candle / level. Moves to breakeven after one more candle confirms its side, then trails "
        "behind the second-to-last candle. No partial profits, no fixed target.",
        "Flat by 16:45 New York. Delta is estimated from 1-minute bars (no real tick data)."])
    return [mg, tr]


# ---------------------------------------------------------------- the 3 hourly winners on the 15-min timeline
def build_h1(d):
    """Hourly candles made from the tower's 15-min candles (only finished hours), with all indicators."""
    x = d[["open", "high", "low", "close", "volume"]]
    hk = x.index.floor("h")
    g = x.groupby(hk)
    raw = pd.DataFrame({"Open": g.open.first(), "High": g.high.max(), "Low": g.low.min(), "Close": g.close.last(),
                        "Volume": g.volume.sum()})
    last15 = pd.Series(x.index, index=x.index).groupby(hk).last()
    end = last15 + pd.Timedelta(minutes=15)
    full_end = raw.index + pd.Timedelta(minutes=60)
    full_end = full_end.where(raw.index.hour != 16, raw.index + pd.Timedelta(minutes=45))
    done = (end.values >= full_end.values) | (raw.index < hk.max())
    raw, last15 = raw[done], last15[done]
    raw.index = raw.index.tz_convert("UTC")
    h = C.add_indicators(C.prepare(raw, "globex", bar=60))
    dec = d.index.get_indexer(pd.DatetimeIndex(last15.reindex(h.index.tz_convert(NY))))
    _H1[id(d)] = (h, dec)
    # hourly values the fighters talk about, shown on the 15-min rows from the moment each hour closes
    for col in ("close", "ema50", "atr", "ch_long", "ch_short", "prev_h", "prev_l"):
        if col in h:
            d["h1_" + col] = _lift(d, dec, h[col].values, ffill=True)
    return h


def _lift(d, dec, vals, ffill=True, fill=np.nan):
    s = pd.Series(np.nan, index=d.index)
    ok = dec >= 0
    s.iloc[dec[ok]] = np.asarray(vals, float)[ok]
    if ffill:
        s = s.groupby(d["date"].values).ffill()       # an hourly decision lasts until the next one, same session only
    return s.fillna(fill).values


def hourly(fn):
    def run(d):
        h, dec = _H1[id(d)]
        out = fn(h)
        fresh = None
        if isinstance(out, tuple):
            out, fresh = out
        tgt = _lift(d, dec, np.asarray(out, float), ffill=True, fill=0.0)
        if fresh is None:
            return tgt
        return tgt, _lift(d, dec, np.asarray(fresh, float), ffill=False, fill=0.0)
    return run


def hourly_roster(lib):
    P = "{h1_close:,.2f}"
    out = []
    nr = dict(lib["NR4 Range Expansion"])
    nr.update(fn=hourly(nr["fn"]), atr_col="h1_atr",
              about="Toby Crabel on 1-HOUR candles: the narrowest hour of the last 4 is usually followed by a burst. "
                    "Survivor of the 2-year prop test.",
              why_l="The last hour was the narrowest of 4, and price burst above it to " + P + ".",
              why_s="The last hour was the narrowest of 4, and price burst below it to " + P + ".",
              watch="Waiting for a narrow 1-hour candle, then a burst out of it.")
    ch = dict(lib["Chandelier Exit Trend"])
    ch.update(fn=hourly(ch["fn"]), atr_col="h1_atr",
              about="Chuck LeBeau's chandelier on 1-HOUR candles: rides a trend until it's 3 hourly ATRs off the extreme. "
                    "Survivor of the 2-year prop test.",
              why_l="Price " + P + " broke above the short-side chandelier ({h1_ch_short:,.2f}) on the hourly chart.",
              why_s="Price " + P + " broke below the long-side chandelier ({h1_ch_long:,.2f}) on the hourly chart.")
    od = dict(lib["Overnight Drift + Trend Filter"])
    od.update(fn=hourly(od["fn"]), atr_col="h1_atr", intraday=True,
              about="The overnight anomaly for a prop account: from midnight New York, holds a long while the hourly trend "
                    "is up (above the 50 EMA), and is always flat by 16:45. Survivor of the 2-year prop test.",
              why_l="After midnight New York and the hourly trend is up (above the 50 EMA {h1_ema50:,.2f}). Holding long.",
              exit_l="The hourly trend broke (below the 50 EMA) or the day ended.",
              watch="Waits for midnight New York, then goes long if price is above the hourly 50 EMA.")
    for s_ in (nr, ch, od):
        s_["tf"] = "1h"
        s_["rules"] = None
        out.append(s_)
    return out


# ---------------------------------------------------------------- roll guard for the 24-hour chart
def roll_adjust_ratio(df, qqq_raw):
    """Yahoo's NQ=F jumps to the next quarterly contract (Mar/Jun/Sep/Dec). QQQ doesn't, so the NQ/QQQ price ratio
    steps up for good at the switch. Find that step, back-adjust earlier prices by it (like charting platforms do)
    and fix the switch candle itself. Returns (df, [(time, gap)])."""
    q = qqq_raw["Close"] if "Close" in qqq_raw else qqq_raw["close"]
    q = q.copy()
    q.index = pd.to_datetime(q.index, utc=True).tz_convert(NY)
    q = q[~q.index.duplicated(keep="last")].sort_index()
    m = pd.merge_asof(pd.DataFrame({"t": df.index, "c": df.close.values}), pd.DataFrame({"t": q.index, "q": q.values}),
                      on="t", direction="backward", tolerance=pd.Timedelta(minutes=14))
    r = pd.Series((m.c / m.q).values, index=df.index).dropna()
    if len(r) < 20:
        return df, []
    before = r.shift(1).rolling(10).median()
    after = r[::-1].shift(1).rolling(10).median()[::-1]
    step = after / before - 1
    rolls, last_t = [], None
    for t, v in step.items():
        if v > 0.004 and t.month in (3, 6, 9, 12) and 7 <= t.day <= 22 and (last_t is None or (t - last_t).days > 20):
            win = df.loc[t - pd.Timedelta(days=2): t + pd.Timedelta(days=1)]
            tj = (win.close / win.close.shift() - 1).abs().idxmax()
            gap = float((after[t] - before[t]) * q.asof(t))
            if gap == gap:
                rolls.append((tj, round(gap, 2)))
            last_t = t
    if not rolls:
        return df, []
    df = df.copy()
    for tj, gap in rolls:
        i = df.index.get_loc(tj)
        o_, h_, l_, c_ = (df[k].values.copy() for k in ("open", "high", "low", "close"))
        for a in (o_, h_, l_, c_):
            a[:i] += gap
        o_[i] += gap
        if gap > 0:
            l_[i] += gap
        else:
            h_[i] += gap
        h_[i] = max(h_[i], o_[i], c_[i])
        l_[i] = min(l_[i], o_[i], c_[i])
        df["open"], df["high"], df["low"], df["close"] = o_, h_, l_, c_
    return df, rolls
