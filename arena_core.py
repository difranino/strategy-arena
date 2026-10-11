# ===================== NASDAQ STRATEGY ARENA — core engine =====================
# Data prep, indicators, a no-lookahead backtest engine, scoring and plain-English reasons.
import warnings
import numpy as np
import pandas as pd

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
NY = "America/New_York"
UK = "Europe/London"


# ---------------------------------------------------------------- data prep
def prepare(raw, market="rth"):
    """raw: DataFrame with Open/High/Low/Close/Volume and a DatetimeIndex.
    market="rth": US regular hours 15-min bars (9:30 to 15:45 bar starts), sessions in New York time.
    market="crypto": 24/7 15-min bars, one session = one UK calendar day (00:00-24:00 London)."""
    tz = NY if market == "rth" else UK
    df = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].copy()
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df.index = idx.tz_convert(tz)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    mins = df.index.hour * 60 + df.index.minute
    df = df[mins % 15 == 0]
    mins = df.index.hour * 60 + df.index.minute
    if market == "rth":
        df = df[(mins >= 9 * 60 + 30) & (mins <= 15 * 60 + 45)]
        df = df[df.index.dayofweek < 5]
    df = df.dropna(subset=["open", "high", "low", "close"])
    df["volume"] = df["volume"].fillna(0)
    df["date"] = df.index.date
    cnt = df.groupby("date")["close"].transform("size")
    keep_n = 20 if market == "rth" else 80
    df = df[(cnt >= keep_n) | (df["date"] == df["date"].iloc[-1])].copy()
    m = df.index.hour * 60 + df.index.minute
    if market == "rth":
        df["k"] = (m - (9 * 60 + 30)) // 15  # 0 = 9:30 bar
        df["nbars"] = 26
        df["last"] = df["k"] == 25  # the 15:45-16:00 bar
    else:
        df["k"] = m // 15  # 0 = 00:00 UK bar
        df["nbars"] = 96
        df["last"] = m == 23 * 60 + 45  # the 23:45-00:00 bar
    ny = df.index.tz_convert(NY)
    df["ny_mins"] = ny.hour * 60 + ny.minute
    df.attrs["market"] = market
    df.attrs["bpd"] = 26 if market == "rth" else 96
    return df


def roll_adjust(fut, ref, threshold=0.0025):
    """Futures roll guard. Yahoo's continuous contract (NQ=F) jumps when it switches to the next quarterly
    contract, which would create fake profits and losses. We compare every bar's move with QQQ (same index):
    in roll months (Mar/Jun/Sep/Dec, first 3 weeks), a move that QQQ doesn't share is the roll gap, and all
    earlier prices are shifted by it (back-adjusted), like professional charting platforms do."""
    q = ref["close"].reindex(fut.index)
    rn = fut["close"] / fut["close"].shift() - 1
    rq = q / q.shift() - 1
    idx = fut.index
    window = np.isin(idx.month, [3, 6, 9, 12]) & (idx.day <= 22)
    jumps = np.where(((rn - rq).abs() > threshold).values & window & rq.notna().values)[0]
    if len(jumps) == 0:
        return fut, []
    fut = fut.copy()
    cols = ["open", "high", "low", "close"]
    shifts = np.zeros(len(fut))
    log = []
    c = fut["close"].values
    for i in jumps:
        if i == 0:
            continue
        gap = c[i] - c[i - 1] * (1 + rq.values[i])
        shifts[:i] += gap
        log.append((idx[i], round(float(gap), 2)))
    for col in cols:
        fut[col] = fut[col].values + shifts
    return fut, log


def drop_unfinished(df, now=None):
    """Remove the bar that is still forming, so decisions never change after the fact."""
    now = now or pd.Timestamp.now(tz=NY)
    return df[df.index + pd.Timedelta(minutes=15) <= now]


# ---------------------------------------------------------------- indicators
def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def _wma(s, n):
    n = int(n)
    w = np.arange(1, n + 1, dtype=float)
    return s.rolling(n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


def _rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def add_indicators(df):
    bpd = df.attrs.get("bpd", 26)
    o, h, l, c, v = df.open, df.high, df.low, df.close, df.volume
    g = df.groupby("date")
    for n in (5, 9, 13, 20, 21, 50):
        df[f"ema{n}"] = _ema(c, n)
    df["sma20"] = c.rolling(20).mean()
    df["std20"] = c.rolling(20).std()
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["tr"] = tr
    df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["rsi2"] = _rsi(c, 2)
    df["rsi14"] = _rsi(c, 14)
    df["macd"] = _ema(c, 12) - _ema(c, 26)
    df["macds"] = _ema(df["macd"], 9)
    df["macdh"] = df.macd - df.macds
    df["bbu"] = df.sma20 + 2 * df.std20
    df["bbl"] = df.sma20 - 2 * df.std20
    df["bbw"] = (df.bbu - df.bbl) / df.sma20
    df["bbw_rank"] = df["bbw"].rolling(120, min_periods=40).rank(pct=True)
    df["kcu"] = df.ema20 + 2 * df.atr
    df["kcl"] = df.ema20 - 2 * df.atr
    for n in (10, 20, 55):
        df[f"dch{n}"] = h.rolling(n).max().shift(1)
        df[f"dcl{n}"] = l.rolling(n).min().shift(1)
    # session VWAP with standard-deviation bands
    tp = (h + l + c) / 3
    df["tp"] = tp
    pv = (tp * v).groupby(df["date"]).cumsum()
    vv = v.groupby(df["date"]).cumsum().replace(0, np.nan)
    df["vwap"] = (pv / vv).fillna(tp.groupby(df["date"]).transform(lambda s: s.expanding().mean()))
    p2 = (tp * tp * v).groupby(df["date"]).cumsum()
    var = (p2 / vv - df["vwap"] ** 2).clip(lower=0)
    df["vwap_sd"] = np.sqrt(var).fillna(0)
    df["vwap_l2"] = df.vwap - 2 * df.vwap_sd
    df["vwap_u2"] = df.vwap + 2 * df.vwap_sd
    # day reference levels
    df["dopen"] = g["open"].transform("first")
    daily = g.agg(dh=("high", "max"), dl=("low", "min"), dc=("close", "last"))
    prev = daily.shift(1)
    df["pdh"] = df["date"].map(prev["dh"])
    df["pdl"] = df["date"].map(prev["dl"])
    df["pdc"] = df["date"].map(prev["dc"])
    df["ppdc"] = df["date"].map(daily["dc"].shift(2))
    df["pdret"] = df.pdc / df.ppdc - 1
    df["prange"] = df["pdh"] - df["pdl"]
    df["gap"] = df.dopen / df.pdc - 1
    df["dayret"] = c / df.pdc - 1
    df["lw_up"] = df.dopen + 0.5 * df.prange
    df["lw_dn"] = df.dopen - 0.5 * df.prange
    # classic floor pivots and Camarilla levels from yesterday
    P = (df.pdh + df.pdl + df.pdc) / 3
    df["piv"], df["r1"], df["s1"] = P, 2 * P - df.pdl, 2 * P - df.pdh
    df["cam_h3"] = df.pdc + 1.1 * df.prange / 4
    df["cam_l3"] = df.pdc - 1.1 * df.prange / 4
    df["cam_h4"] = df.pdc + 1.1 * df.prange / 2
    df["cam_l4"] = df.pdc - 1.1 * df.prange / 2
    # opening range highs/lows over the first n bars, available once those bars are done
    for n in (1, 2, 4):
        hh = g["high"].transform(lambda s, n=n: s.iloc[:n].max())
        ll = g["low"].transform(lambda s, n=n: s.iloc[:n].min())
        ok = df["k"] >= n - 1
        df[f"orh{n}"] = hh.where(ok)
        df[f"orl{n}"] = ll.where(ok)
    # first-30-min return (known from the 9:45 bar's close onward)
    c1 = g["close"].transform(lambda s: s.iloc[1] if len(s) > 1 else np.nan)
    df["first30"] = (c1 / df.pdc - 1).where(df.k >= 1)
    # morning move to the 12:45 close (known from that bar onward) for the afternoon strategies
    c13 = g["close"].transform(lambda s: s.iloc[13] if len(s) > 13 else np.nan)
    df["am_ret"] = (c13 / df.dopen - 1).where(df.k >= 13)
    # stochastic, Williams %R, CCI, MFI
    ll14, hh14 = l.rolling(14).min(), h.rolling(14).max()
    rng14 = (hh14 - ll14).replace(0, np.nan)
    df["stk"] = (100 * (c - ll14) / rng14).fillna(50).rolling(3).mean()
    df["std_"] = df["stk"].rolling(3).mean()
    df["willr"] = (-100 * (hh14 - c) / rng14).fillna(-50)
    sma_tp = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    df["cci"] = ((tp - sma_tp) / (0.015 * mad.replace(0, np.nan))).fillna(0)
    mf = tp * v
    pos_mf = mf.where(tp > tp.shift(), 0.0).rolling(14).sum()
    neg_mf = mf.where(tp < tp.shift(), 0.0).rolling(14).sum()
    df["mfi"] = (100 - 100 / (1 + pos_mf / neg_mf.replace(0, np.nan))).fillna(50)
    # ADX / DI
    upm, dnm = h.diff(), -l.diff()
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0)
    mdm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    atr_w = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["pdi"] = 100 * pd.Series(pdm, index=df.index).ewm(alpha=1 / 14, adjust=False).mean() / atr_w
    df["mdi"] = 100 * pd.Series(mdm, index=df.index).ewm(alpha=1 / 14, adjust=False).mean() / atr_w
    dx = 100 * (df.pdi - df.mdi).abs() / (df.pdi + df.mdi).replace(0, np.nan)
    df["adx"] = dx.fillna(0).ewm(alpha=1 / 14, adjust=False).mean()
    # trend followers
    df["st_dir"] = _supertrend(h.values, l.values, c.values, tr.ewm(alpha=1 / 10, adjust=False).mean().values, 3.0)
    df["psar_dir"] = _psar(h.values, l.values)
    tenkan = (h.rolling(9).max() + l.rolling(9).min()) / 2
    kijun = (h.rolling(26).max() + l.rolling(26).min()) / 2
    df["tenkan"], df["kijun"] = tenkan, kijun
    df["spanA"] = ((tenkan + kijun) / 2).shift(26)
    df["spanB"] = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    df["cloud_top"] = np.fmax(df.spanA, df.spanB)
    df["cloud_bot"] = np.fmin(df.spanA, df.spanB)
    hac = (o + h + l + c) / 4
    hao = np.empty(len(df))
    hao[0] = (o.iloc[0] + c.iloc[0]) / 2
    hv = hac.values
    for i in range(1, len(df)):
        hao[i] = (hao[i - 1] + hv[i - 1]) / 2
    df["ha_dir"] = np.sign(hv - hao)
    df["hma"] = _wma(2 * _wma(c, 10) - _wma(c, 21), int(np.sqrt(21)))
    df["hma_slope"] = df.hma.diff()
    df["kama"] = _kama(c.values)
    df["kama_slope"] = pd.Series(df["kama"].values, index=df.index).diff()
    hi_age = h.rolling(26).apply(lambda x: 25 - np.argmax(x), raw=True)
    lo_age = l.rolling(26).apply(lambda x: 25 - np.argmin(x), raw=True)
    df["aroon_up"] = 100 * (25 - hi_age) / 25
    df["aroon_dn"] = 100 * (25 - lo_age) / 25
    df["ch_long"] = h.rolling(22).max() - 3 * df.atr
    df["ch_short"] = l.rolling(22).min() + 3 * df.atr
    df["ch_dir"] = _chandelier(c.values, df.ch_long.values, df.ch_short.values)
    df["ema13_slope"] = df.ema13.diff()
    df["macdh_slope"] = df.macdh.diff()
    df["impulse"] = np.where((df.ema13_slope > 0) & (df.macdh_slope > 0), 1,
                             np.where((df.ema13_slope < 0) & (df.macdh_slope < 0), -1, 0))
    n = 20
    w = np.arange(n) - (n - 1) / 2
    df["lr_slope"] = c.rolling(n).apply(lambda x: np.dot(x, w) / np.dot(w, w), raw=True)
    vmp = (h - l.shift()).abs().rolling(14).sum()
    vmm = (l - h.shift()).abs().rolling(14).sum()
    trs = tr.rolling(14).sum().replace(0, np.nan)
    df["vi_p"], df["vi_m"] = vmp / trs, vmm / trs
    e3 = _ema(_ema(_ema(c, 15), 15), 15)
    df["trix"] = 100 * e3.pct_change()
    df["trix_s"] = _ema(df["trix"], 9)
    # bar patterns
    rng = (h - l).replace(0, np.nan)
    body = c - o
    df["lower_wick"] = np.minimum(o, c) - l
    df["upper_wick"] = h - np.maximum(o, c)
    df["pin_bull"] = (df.lower_wick >= 0.6 * rng) & (body.abs() <= 0.3 * rng)
    df["pin_bear"] = (df.upper_wick >= 0.6 * rng) & (body.abs() <= 0.3 * rng)
    po, pc = o.shift(), c.shift()
    df["engulf_bull"] = (pc < po) & (c > o) & (o <= pc) & (c >= po)
    df["engulf_bear"] = (pc > po) & (c < o) & (o >= pc) & (c <= po)
    df["inside_prev"] = (h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2))
    df["mother_h"], df["mother_l"] = h.shift(2), l.shift(2)
    r = h - l
    df["nr4_prev"] = r.shift(1) <= r.shift(1).rolling(4).min()
    df["prev_h"], df["prev_l"] = h.shift(1), l.shift(1)
    df["vol_ratio"] = (v / v.rolling(20).mean().replace(0, np.nan)).fillna(1)
    df["range_atr"] = (h - l) / df.atr.shift().replace(0, np.nan)
    df["down3"] = (c < c.shift()) & (c.shift() < c.shift(2)) & (c.shift(2) < c.shift(3))
    df["up3"] = (c > c.shift()) & (c.shift() > c.shift(2)) & (c.shift(2) > c.shift(3))
    df["ret5d"] = c / c.shift(bpd * 5) - 1
    df["ret1h"] = c / c.shift(4) - 1
    df["ema_1h20"] = _ema(c, 4 * 20)
    df["ema_4h20"] = _ema(c, 16 * 20)
    df["ema_4h50"] = _ema(c, 16 * 50)
    df["dch_day"] = h.rolling(bpd).max().shift(1)
    df["dcl_day"] = l.rolling(bpd).min().shift(1)
    df["dcl_half"] = l.rolling(max(bpd // 2, 10)).min().shift(1)
    df["dch_half"] = h.rolling(max(bpd // 2, 10)).max().shift(1)
    lo_d, hi_d = g["low"].cummin(), g["high"].cummax()
    df["day_pos"] = ((c - lo_d) / (hi_d - lo_d).replace(0, np.nan)).fillna(0.5)
    # crypto: Asia session range (00:00-07:00 UK), known from the 06:45 bar onward
    if df.attrs.get("market") == "crypto":
        ah = g["high"].transform(lambda s_: s_.iloc[:28].max())
        al = g["low"].transform(lambda s_: s_.iloc[:28].min())
        df["asia_h"] = ah.where(df.k >= 27)
        df["asia_l"] = al.where(df.k >= 27)
    df["zscore"] = (c - c.rolling(50).mean()) / c.rolling(50).std().replace(0, np.nan)
    df["dow"] = df.index.dayofweek
    return df


def _supertrend(h, l, c, atr, m):
    n = len(c)
    d = np.ones(n)
    ub = (h + l) / 2 + m * atr
    lb = (h + l) / 2 - m * atr
    fu, fl = ub.copy(), lb.copy()
    for i in range(1, n):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if c[i] > fu[i - 1]:
            d[i] = 1
        elif c[i] < fl[i - 1]:
            d[i] = -1
        else:
            d[i] = d[i - 1]
    return d


def _psar(h, l, step=0.02, mx=0.2):
    n = len(h)
    d = np.ones(n)
    up, af, ep, sar = True, step, h[0], l[0]
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if up:
            sar = min(sar, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < sar:
                up, sar, ep, af = False, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(af + step, mx)
        else:
            sar = max(sar, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > sar:
                up, sar, ep, af = True, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(af + step, mx)
        d[i] = 1 if up else -1
    return d


def _kama(c, n=10, fast=2, slow=30):
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    fsc, ssc = 2 / (fast + 1), 2 / (slow + 1)
    out[n] = c[n]
    for i in range(n + 1, len(c)):
        change = abs(c[i] - c[i - n])
        vol = np.sum(np.abs(np.diff(c[i - n:i + 1])))
        er = change / vol if vol > 0 else 0
        sc = (er * (fsc - ssc) + ssc) ** 2
        out[i] = out[i - 1] + sc * (c[i] - out[i - 1])
    return out


def _chandelier(c, lo_stop, hi_stop):
    d = np.zeros(len(c))
    cur = 0
    for i in range(len(c)):
        if not np.isnan(hi_stop[i]) and c[i] > hi_stop[i]:
            cur = 1
        elif not np.isnan(lo_stop[i]) and c[i] < lo_stop[i]:
            cur = -1
        d[i] = cur
    return d


# ---------------------------------------------------------------- signal helpers
# Every strategy returns a target position (+1 long, -1 short, 0 flat) decided at the
# CLOSE of each bar. The engine fills it at the NEXT bar's open, so nothing sees the future.
def condition(df, long_c, short_c=None):
    t = np.where(np.asarray(long_c, bool), 1, 0)
    if short_c is not None:
        t = np.where(np.asarray(short_c, bool), -1, t)
    return t.astype(float)


def once_per_day(df, long_trig, short_trig, start_k=0, last_entry_k=99):
    """Trigger-style trading: a fresh trigger (condition turns true) opens a trade that is held until
    its stop/target, the opposite trigger or the end of the session. After an exit, a NEW trigger
    in the same direction can open another trade, as many times a day as the setup shows up.
    Returns (target, fresh) where fresh marks the bars with a new trigger (+1 long / -1 short)."""
    lt = np.asarray(long_trig, bool)
    st = np.asarray(short_trig, bool)
    k = df["k"].values
    n = len(df)
    t = np.zeros(n)
    fresh = np.zeros(n)
    pos = 0
    for i in range(n):
        if k[i] == 0 or (i > 0 and k[i] < k[i - 1]):
            pos = 0
        ok = start_k <= k[i] <= last_entry_k
        new_l = lt[i] and not (i > 0 and lt[i - 1] and k[i] != 0)
        new_s = st[i] and not (i > 0 and st[i - 1] and k[i] != 0)
        if ok and new_l:
            pos, fresh[i] = 1, 1
        elif ok and new_s:
            pos, fresh[i] = -1, -1
        t[i] = pos
    return t, fresh


trigger_trade = once_per_day


def enter_exit(df, le, lx, se=None, sx=None, last_entry_k=99):
    """Enter on an entry condition, hold until the matching exit condition."""
    le, lx = np.asarray(le, bool), np.asarray(lx, bool)
    se = np.zeros(len(df), bool) if se is None else np.asarray(se, bool)
    sx = np.zeros(len(df), bool) if sx is None else np.asarray(sx, bool)
    k = df["k"].values
    t = np.zeros(len(df))
    pos = 0
    for i in range(len(df)):
        if k[i] == 0:
            pos = 0
        if pos == 1 and lx[i]:
            pos = 0
        elif pos == -1 and sx[i]:
            pos = 0
        if pos == 0 and k[i] <= last_entry_k:
            if le[i]:
                pos = 1
            elif se[i]:
                pos = -1
        t[i] = pos
    return t


def cross_up(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
    pa, pb = np.roll(a, 1), np.roll(b, 1)
    out = (a > b) & (pa <= pb)
    out[0] = False
    return out


def cross_dn(a, b):
    return cross_up(b, a)


# ---------------------------------------------------------------- plain-English reasons
_FIELDS = {}


def say(template, row, fallback=""):
    """Fill a reason template like 'Closed {close:,.2f} above {orh1:,.2f}' from one bar's values."""
    if not template:
        return fallback
    try:
        if template not in _FIELDS:
            import string
            _FIELDS[template] = [f for _, f, _, _ in string.Formatter().parse(template) if f]
        vals = {}
        for f in _FIELDS[template]:
            v = row[f]
            if v is None or (isinstance(v, (float, np.floating)) and np.isnan(v)):
                return fallback
            vals[f] = v
        return template.format(**vals)
    except Exception:
        return fallback


# ---------------------------------------------------------------- engine
_ROWS = {}


class _Row:
    __slots__ = ("df", "i")

    def __init__(self, df, i):
        self.df, self.i = df, int(i)

    def __getitem__(self, k):
        return self.df[k].values[self.i]


def row_at(df, i):
    """One bar's values (looked up lazily), used to fill reason templates."""
    return _Row(df, i)


def exit_text(strat, side, reason, px, row):
    if reason == "stop":
        return f"Stopped out at {px:,.2f}. The protective stop ({strat['stop']}× ATR) was hit."
    if reason == "target":
        return f"Profit target hit at {px:,.2f}."
    if reason == "close":
        return (f"End of the day: closed at {px:,.2f}." if strat.get("market") == "crypto"
                else f"Closing bell: closed at {px:,.2f}. It never holds overnight.")
    if reason == "flip":
        return f"Signal flipped the other way at {px:,.2f}."
    tmpl = strat.get("exit_l") if side > 0 else strat.get("exit_s")
    return say(tmpl, row, "") or "Its exit rule fired."


def why_in(df, strat, side, dec_i):
    return say(strat["why_l"] if side > 0 else strat.get("why_s"), row_at(df, dec_i), strat["about"])


def why_out(df, strat, side, reason, px, dec_i):
    return exit_text(strat, side, reason, px, row_at(df, dec_i))


def backtest(df, strat, point_value=2.0, cost_rt=2.50, contracts=1, notional=None, cost_pct=None,
             asset="", tgt=None):
    """Fills at next bar open, stops/targets checked on the bar's high/low (stop wins if both hit),
    intraday strategies flattened at the session's last close.
    Sizing: futures = point_value x contracts; stocks/crypto = a fixed $ notional per trade.
    Costs: cost_rt dollars per round trip, or cost_pct of the notional.
    Every trade stores why it went in and why it came out, in plain English."""
    if tgt is None:
        tgt = strat["fn"](df)
    fresh = None
    if isinstance(tgt, tuple):
        tgt, fresh = tgt
    tgt = np.nan_to_num(np.asarray(tgt, float))
    fresh = np.zeros(len(tgt)) if fresh is None else np.asarray(fresh, float)
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    atr = df["atr"].values
    last = df["last"].values
    idx = df.index
    n = len(df)
    st = dict(pos=0, entry=0.0, ent_i=None, stop=None, tp=None, units=0.0)
    blocked = 0
    trades = []
    eq = np.zeros(n)
    realized = 0.0
    tag = (asset + ": ") if asset else ""

    def units_for(px):
        return (notional / px) if notional else point_value * contracts

    def cost():
        return (cost_pct * notional) if (notional and cost_pct is not None) else cost_rt * contracts

    def close_trade(px, i, why, dec_i):
        nonlocal realized
        p = st["pos"]
        pnl = (px - st["entry"]) * p * st["units"] - cost()
        trades.append((asset, st["ent_i"], i, p, st["entry"], px, pnl, why, st["ent_i"] - 1, dec_i, st["stop"], st["tp"]))
        realized += pnl
        st["pos"] = 0

    for i in range(1, n):
        want = tgt[i - 1]
        if strat["intraday"] and last[i - 1]:
            want = 0
        if blocked and (want != blocked or fresh[i - 1] == blocked):
            blocked = 0
        if blocked and want == blocked:
            want = 0
        if want != st["pos"]:
            if st["pos"] != 0:
                close_trade(o[i], i, "flip" if want == -st["pos"] else "signal", i - 1)
            if want != 0:
                p = int(want)
                st.update(pos=p, entry=o[i], ent_i=i, units=units_for(o[i]))
                a = atr[i - 1]
                st["stop"] = o[i] - p * strat["stop"] * a if strat["stop"] else None
                st["tp"] = o[i] + p * strat["tp"] * a if strat["tp"] else None
        p = st["pos"]
        if p != 0:
            sp, tp_ = st["stop"], st["tp"]
            hit_stop = sp is not None and ((p > 0 and l[i] <= sp) or (p < 0 and h[i] >= sp))
            hit_tp = tp_ is not None and ((p > 0 and h[i] >= tp_) or (p < 0 and l[i] <= tp_))
            if hit_stop:
                px = min(o[i], sp) if p > 0 else max(o[i], sp)
                close_trade(px, i, "stop", i)
                blocked = p
            elif hit_tp:
                close_trade(max(o[i], tp_) if p > 0 else min(o[i], tp_), i, "target", i)
                blocked = p
        if st["pos"] != 0 and strat["intraday"] and last[i]:
            close_trade(c[i], i, "close", i)
        eq[i] = realized + ((c[i] - st["entry"]) * st["pos"] * st["units"] if st["pos"] != 0 else 0.0)
    cols = ["asset", "entry_i", "exit_i", "side", "entry", "exit", "pnl", "exit_reason", "in_dec", "out_dec", "stop", "target"]
    tr = pd.DataFrame(trades, columns=cols)
    tr["entry_time"] = idx[tr.entry_i.values.astype(int)] if len(tr) else pd.DatetimeIndex([], tz=idx.tz)
    tr["exit_time"] = idx[tr.exit_i.values.astype(int)] if len(tr) else pd.DatetimeIndex([], tz=idx.tz)
    # a "close" exit happens at the END of its bar
    if len(tr):
        tr.loc[tr.exit_reason == "close", "exit_time"] = tr.loc[tr.exit_reason == "close", "exit_time"] + pd.Timedelta(minutes=15)
    tr.attrs["equity"] = pd.Series(eq, index=idx)
    tr.attrs["open"] = []
    if st["pos"] != 0:
        tr.attrs["open"] = [dict(asset=asset, side=st["pos"], entry=st["entry"], entry_time=idx[st["ent_i"]],
                                 stop=st["stop"], target=st["tp"], in_dec=st["ent_i"] - 1,
                                 upnl=(c[n - 1] - st["entry"]) * st["pos"] * st["units"])]
    return tr


def score(trades, start=None, end=None):
    """Scores one window. Profit and drawdown use mark-to-market equity, so open positions
    count; win rate and profit factor use trades closed in the window."""
    eqs = trades.attrs["equity"]
    w = eqs
    base = 0.0
    if start is not None:
        prev = eqs[eqs.index < start]
        base = prev.iloc[-1] if len(prev) else 0.0
        w = eqs[eqs.index >= start]
    if end is not None:
        w = w[w.index < end]
    t = trades
    if start is not None:
        t = t[t.exit_time >= start]
    if end is not None:
        t = t[t.exit_time < end]
    if len(w) == 0:
        return dict(trades=0, net=0.0, win=np.nan, pf=np.nan, avg=np.nan, maxdd=0.0, sharpe=np.nan, curve=None)
    curve = np.concatenate([[base], w.values]) - base
    dd = float(np.max(np.maximum.accumulate(curve) - curve))
    dl = w.groupby(w.index.date).last()
    daily = dl.diff()
    daily.iloc[0] = dl.iloc[0] - base
    sh = daily.mean() / daily.std() * np.sqrt(252) if len(daily) > 2 and daily.std() > 0 else np.nan
    pnl = t.pnl.values
    gw, gl = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    return dict(trades=len(t), net=float(curve[-1]), win=float((pnl > 0).mean()) if len(t) else np.nan,
                pf=(float(gw / gl) if gl > 0 else (np.inf if gw > 0 else np.nan)),
                avg=float(pnl.mean()) if len(t) else np.nan, maxdd=dd, sharpe=float(sh) if sh == sh else np.nan,
                curve=pd.Series(curve[1:], index=w.index))
