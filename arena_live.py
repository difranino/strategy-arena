# ===================== STRATEGY ARENA — data, building the 4 arenas, live loop =====================
import os, time
import pandas as pd
import arena_core as C
import arena_season as SE
import arena_strats as NQS
import arena_stocks as STK
import arena_crypto as CRY
import arena_social as SOC
import arena_hub as H

NY, UK = "America/New_York", "Europe/London"


def cache_dir(use_drive=True):
    if use_drive:
        try:
            from google.colab import drive
            if not os.path.exists("/content/drive/MyDrive"):
                drive.mount("/content/drive")
            d = "/content/drive/MyDrive/NasdaqArena"
            os.makedirs(d, exist_ok=True)
            return d, True
        except Exception as e:
            print(f"Google Drive not available ({e}). Using temporary storage for this session only.")
    d = "/content/arena_cache" if os.path.exists("/content") else "arena_cache"
    os.makedirs(d, exist_ok=True)
    return d, False


def _path(folder, sym):
    return os.path.join(folder, f"bars_{sym.replace('=', '_')}.csv")


def load_symbols(syms, folder, prepost=False):
    """Downloads the latest 15-min bars for several symbols and merges them into the saved history,
    so each season keeps its full past even after Yahoo's 60-day window moves on."""
    import yfinance as yf
    old = {}
    for s in syms:
        p = _path(folder, s)
        if os.path.exists(p):
            o = pd.read_csv(p, index_col=0)
            o.index = pd.to_datetime(o.index, utc=True)
            old[s] = o
    fresh_enough = all(s in old and (pd.Timestamp.now(tz="UTC") - old[s].index.max()).days <= 6 for s in syms)
    period = "8d" if fresh_enough else "60d"
    new = {}
    try:
        raw = yf.download(syms, period=period, interval="15m", prepost=prepost, group_by="ticker",
                          auto_adjust=False, threads=True, progress=False)
        for s in syms:
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    lv0 = raw.columns.get_level_values(0)
                    x = raw[s] if s in lv0 else raw.xs(s, axis=1, level=1)
                else:
                    x = raw
                x = x[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
                x.index = pd.to_datetime(x.index, utc=True)
                new[s] = x
            except Exception:
                pass
    except Exception as e:
        print(f"Download problem ({e}). Using saved data where possible.")
    out = {}
    for s in syms:
        parts = [x for x in (old.get(s), new.get(s)) if x is not None and len(x)]
        if not parts:
            continue
        allb = pd.concat(parts)
        allb = allb[~allb.index.duplicated(keep="last")].sort_index()
        allb.to_csv(_path(folder, s))
        out[s] = allb
    return out


def _prep(raw, market, now):
    d = C.prepare(raw, market)
    d = C.drop_unfinished(d, now)
    return C.add_indicators(d)


class Settings:
    def __init__(self, **kw):
        self.__dict__.update(dict(nq_start="2026-10-07", new_start="2026-10-09", ko_nq=3, ko_stocks=3, ko_crypto=3,
                                  ko_hype=1, nq_symbol="NQ=F", point_value=2.0, nq_cost=2.5, stock_size=10000.0,
                                  stock_cost_pct=0.0005, crypto_size=10000.0, crypto_cost_pct=0.0015))
        self.__dict__.update(kw)


def build_nq(st, folder, now, raw=None):
    if raw is None:
        got = load_symbols([st.nq_symbol], folder, prepost=True)
        raw = got.get(st.nq_symbol)
        if raw is None:
            got = load_symbols(["MNQ=F"], folder, prepost=True)
            raw = got["MNQ=F"]
    df = _prep(raw, "rth", now)
    df["asset"] = "NQ"
    A = SE.Arena("nq", "Nasdaq Futures", "⚡", {"NQ": df}, df, NQS.original_roster(), NQS.challenger_pool(),
                 NQS.benchmark(), SE.Cfg(st.nq_start, ko_per_day=st.ko_nq),
                 dict(point_value=st.point_value, cost_rt=st.nq_cost), market="rth", unit_label="contract",
                 extra=dict(sizing_text=f"1 MNQ contract (${st.point_value:g} per point), ${st.nq_cost:.2f} costs per round trip."))
    return A


def build_stocks(st, folder, now, raws=None):
    syms = STK.STOCKS + [STK.MARKET]
    raws = raws or load_symbols(syms, folder)
    dfs = {s: _prep(raws[s], "rth", now) for s in STK.STOCKS if s in raws}
    spy = _prep(raws[STK.MARKET], "rth", now)
    STK.add_market_cols(dfs, spy)
    sizing = dict(notional=st.stock_size, cost_pct=st.stock_cost_pct)
    A = SE.Arena("stocks", "Stocks", "📈", dfs, spy, STK.roster(), STK.pool(), STK.benchmark(),
                 SE.Cfg(st.new_start, ko_per_day=st.ko_stocks), sizing, market="rth", unit_label="stocks",
                 extra=dict(sizing_text=f"${st.stock_size:,.0f} per position on any of the 9 stocks (long or short), "
                                        f"{st.stock_cost_pct * 100:.2f}% costs per round trip."))
    return A, dfs, spy


def build_crypto(st, folder, now, raws=None):
    raws = raws or load_symbols(CRY.COINS, folder)
    dfs = {s: _prep(raws[s], "crypto", now) for s in CRY.COINS if s in raws}
    CRY.add_crypto_cols(dfs)
    master = dfs["BTC-USD"]
    sizing = dict(notional=st.crypto_size, cost_pct=st.crypto_cost_pct)
    A = SE.Arena("crypto", "Crypto", "₿", dfs, master, CRY.roster(), CRY.pool(), CRY.benchmark(),
                 SE.Cfg(st.new_start, ko_per_day=st.ko_crypto, week_len=7), sizing, market="crypto", unit_label="coins",
                 extra=dict(sizing_text=f"${st.crypto_size:,.0f} per position on BTC, ETH or SOL (long or short), "
                                        f"{st.crypto_cost_pct * 100:.2f}% costs per round trip. Trades 24/7; a session is one UK day."))
    return A


def build_hype(st, folder, now, stock_dfs, spy, news=None, reddit=None):
    dfs = {a: d.copy() for a, d in stock_dfs.items()}
    if news is None:
        news = SOC.fetch_news(folder, list(dfs))
    if reddit is None:
        reddit = SOC.fetch_reddit(folder, list(dfs))
    SOC.add_social_cols(dfs, news, reddit)
    sizing = dict(notional=st.stock_size, cost_pct=st.stock_cost_pct)
    A = SE.Arena("hype", "Hype", "🗣️", dfs, spy, SOC.roster(), SOC.pool(), STK.benchmark(),
                 SE.Cfg(st.new_start, ko_per_day=st.ko_hype), sizing, market="rth", unit_label="stocks",
                 crown_needs_qual=False, pool_needs_qual=False,
                 extra=dict(sizing_text=f"${st.stock_size:,.0f} per position on the same 9 stocks, trading on Reddit chatter "
                                        f"and news-headline mood. {st.stock_cost_pct * 100:.2f}% costs per round trip.",
                            headlines=SOC.latest_headlines(news, 25), reddit=SOC.reddit_board(reddit)))
    return A


def build_all(st, folder, now=None, which=("nq", "stocks", "crypto", "hype"), cache=None, reload_sec=None):
    now = now or pd.Timestamp.now(tz=NY)
    cache = cache if cache is not None else {}
    errs = []
    stock_parts = None
    for key in which:
        try:
            if key == "nq":
                A = build_nq(st, folder, now)
            elif key == "stocks":
                A, sd, spy = build_stocks(st, folder, now)
                stock_parts = (sd, spy)
            elif key == "crypto":
                A = build_crypto(st, folder, now)
            elif key == "hype":
                if stock_parts is None:
                    _, sd, spy = build_stocks(st, folder, now)
                    stock_parts = (sd, spy)
                A = build_hype(st, folder, now, *stock_parts)
            S = SE.run_season(A, now)
            cache[key] = SE.game_state(A, S)
        except Exception as e:
            import traceback
            traceback.print_exc()
            errs.append(f"{key}: {e}")
    order = [k for k in ("nq", "stocks", "crypto", "hype") if k in cache]
    return H.render(cache, order, reload_sec), cache, errs


def us_open(now=None):
    n = (now or pd.Timestamp.now(tz=NY)).tz_convert(NY)
    return n.dayofweek < 5 and (9, 30) <= (n.hour, n.minute) < (16, 20)


def run_live(st, use_drive=True, max_hours=11):
    from IPython.display import HTML, display
    folder, on_drive = cache_dir(use_drive)
    print(("Season history saved to Google Drive → MyDrive/NasdaqArena" if on_drive else "History kept for this session only."))
    handle = display(HTML("<div style='padding:20px;font:14px sans-serif'>Loading the 4 arenas… (about a minute the first time)</div>"),
                     display_id=True)
    cache, t0, first = {}, time.time(), True
    while True:
        now = pd.Timestamp.now(tz=NY)
        which = ["crypto"] + (["nq", "stocks", "hype"] if (first or us_open(now)) else [])
        html, cache, errs = build_all(st, folder, now, which=which, cache=cache)
        if errs:
            html = ("<div style='padding:8px;font:12px sans-serif;color:#c00'>Some arenas could not update: "
                    + "; ".join(errs) + "</div>") + html
        handle.update(HTML(html))
        first = False
        if (time.time() - t0) / 3600 > max_hours:
            print("Stopped after many hours. Press Run all again to continue.")
            break
        now = pd.Timestamp.now(tz=NY)
        nxt = now.floor("15min") + pd.Timedelta(minutes=15, seconds=90)
        time.sleep(max(30, (nxt - now).total_seconds()))
