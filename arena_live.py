# ===================== STRATEGY ARENA — data, building the 4 arenas, live loop =====================
import os, time
import pandas as pd
import arena_core as C
import arena_season as SE
import arena_prop as PR
import arena_strats as NQS
import arena_stocks as STK
import arena_crypto as CRY
import arena_social as SOC
import arena_world as AW
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
                                  ko_hype=1, nq_symbol="NQ=F", point_value=20.0, nq_contracts=3, nq_cost=14.0, stock_size=10000.0,
                                  stock_cost_pct=0.0005, crypto_size=10000.0, crypto_cost_pct=0.0015,
                                  finals_at="2026-10-16T21:00:00+01:00", repo="difranino/strategy-arena",
                                  risk_limits={"nq": 2000, "stocks": 1500, "crypto": 1000, "hype": 1500},
                                  prop={"nq": dict(PR.PROP)},
                                  revive={"nq": {"Overnight Drift": "2026-10-12"}}, monkeys=20, grace=3,
                                  news_join="2026-10-13"))
        self.__dict__.update(kw)


def build_nq(st, folder, now, raw=None):
    if raw is None:
        got = load_symbols([st.nq_symbol], folder, prepost=True)
        raw = got.get(st.nq_symbol)
        if raw is None:
            got = load_symbols(["MNQ=F"], folder, prepost=True)
            raw = got["MNQ=F"]
    df = C.drop_unfinished(C.prepare(raw, "rth"), now)
    try:  # roll guard: compare with QQQ to remove contract-roll jumps
        ref = C.prepare(load_symbols(["QQQ"], folder)["QQQ"], "rth")
        df, rolls = C.roll_adjust(df, ref)
        if rolls:
            print("Futures roll adjusted:", rolls)
    except Exception as e:
        print(f"Roll guard skipped ({e}).")
    df = C.add_indicators(df)
    df["asset"] = "NQ"
    A = SE.Arena("nq", "Nasdaq Futures", "⚡", {"NQ": df}, df, NQS.original_roster(), NQS.challenger_pool(),
                 NQS.benchmark(), SE.Cfg(st.nq_start, ko_per_day=st.ko_nq, grace=st.grace, revive=st.revive.get("nq")),
                 dict(point_value=st.point_value, cost_rt=st.nq_cost, contracts=st.nq_contracts), market="rth", unit_label="contract",
                 risk_limit=st.risk_limits.get("nq", 1000), monkeys=NQS.monkeys(st.monkeys), prop=st.prop.get("nq"),
                 extra=dict(sizing_text=(f"{st.nq_contracts} NQ mini contracts (${st.point_value:g} per point each = "
                                         f"${st.point_value * st.nq_contracts:g} per point), ${st.nq_cost:g} costs per contract per round trip "
                                         f"(${st.nq_cost * st.nq_contracts:g} per trade).")))
    return A


def build_stocks(st, folder, now, raws=None, world=None):
    syms = STK.STOCKS + [STK.MARKET]
    raws = raws or load_symbols(syms, folder)
    dfs = {s: _prep(raws[s], "rth", now) for s in STK.STOCKS if s in raws}
    spy = _prep(raws[STK.MARKET], "rth", now)
    STK.add_market_cols(dfs, spy)
    if world is None:
        world = AW.fetch_world(folder)
    AW.add_world_cols(dfs, world)
    news_fighters = AW.roster()
    for s_ in news_fighters:
        s_["joins"] = getattr(st, "news_join", None)
    sizing = dict(notional=st.stock_size, cost_pct=st.stock_cost_pct)
    A = SE.Arena("stocks", "Stocks", "📈", dfs, spy, STK.roster() + news_fighters, STK.pool(), STK.benchmark(),
                 SE.Cfg(st.new_start, ko_per_day=st.ko_stocks, grace=st.grace, revive=st.revive.get("stocks")), sizing,
                 market="rth", unit_label="stocks", risk_limit=st.risk_limits.get("stocks", 1000), monkeys=NQS.monkeys(st.monkeys),
                 extra=dict(sizing_text=f"${st.stock_size:,.0f} per position on any of the 9 stocks (long or short), "
                                        f"{st.stock_cost_pct * 100:.2f}% costs per round trip.",
                            headlines=AW.latest_world(world, 30)))
    return A, dfs, spy


def build_crypto(st, folder, now, raws=None):
    raws = raws or load_symbols(CRY.COINS, folder)
    dfs = {s: _prep(raws[s], "crypto", now) for s in CRY.COINS if s in raws}
    CRY.add_crypto_cols(dfs)
    master = dfs["BTC-USD"]
    sizing = dict(notional=st.crypto_size, cost_pct=st.crypto_cost_pct)
    A = SE.Arena("crypto", "Crypto", "₿", dfs, master, CRY.roster(), CRY.pool(), CRY.benchmark(),
                 SE.Cfg(st.new_start, ko_per_day=st.ko_crypto, week_len=7, grace=st.grace, revive=st.revive.get("crypto")), sizing,
                 market="crypto", unit_label="coins", risk_limit=st.risk_limits.get("crypto", 1000), monkeys=NQS.monkeys(st.monkeys),
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
                 SE.Cfg(st.new_start, ko_per_day=st.ko_hype, grace=st.grace, revive=st.revive.get("hype")), sizing,
                 market="rth", unit_label="stocks", risk_limit=st.risk_limits.get("hype", 1000), monkeys=NQS.monkeys(st.monkeys),
                 crown_needs_qual=False, pool_needs_qual=False,
                 extra=dict(sizing_text=f"${st.stock_size:,.0f} per position on the same 9 stocks, trading on Reddit chatter "
                                        f"and news-headline mood. {st.stock_cost_pct * 100:.2f}% costs per round trip.",
                            headlines=SOC.latest_headlines(news, 25), reddit=SOC.reddit_board(reddit)))
    return A


def _hall_of_fame(folder):
    """After the finals: {league: (finals date, [podium names])} from the saved finals.json."""
    import json
    try:
        data = json.load(open(os.path.join(folder, "finals.json")))
    except Exception:
        return {}
    day = pd.Timestamp(data["at"]).tz_convert(NY).date()
    out = {}
    for k, F in data.get("leagues", {}).items():
        pod = F.get("podium") or [x for x in [F.get("winner")] + (F.get("runners") or []) if x]
        out[k] = (day, [r["name"] for r in pod])
    return out


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
            hall = _hall_of_fame(folder).get(key)
            if hall:
                A.cfg.protect, A.cfg.protect_from = set(hall[1]), hall[0]
            S = SE.run_season(A, now)
            cache[key] = SE.game_state(A, S)
        except Exception as e:
            import traceback
            traceback.print_exc()
            errs.append(f"{key}: {e}")
    order = [k for k in ("nq", "stocks", "crypto", "hype") if k in cache]
    add_code_links(cache, os.environ.get("GITHUB_REPOSITORY") or getattr(st, "repo", None))
    frozen = freeze_finals(st, folder, now, cache)
    return H.render(cache, order, reload_sec, final_at=getattr(st, "finals_at", None), frozen=frozen,
                    built_at=pd.Timestamp.now(tz="UTC").isoformat()), cache, errs


def code_index():
    """Where each fighter's rules live in the code, so the site can link straight to them."""
    import re
    idx = {}
    for mod in (NQS, STK, CRY, SOC, AW):
        path = mod.__file__
        for i, line in enumerate(open(path, encoding="utf-8")):
            m = re.search(r'S\("([^"]+)"', line)
            if m and m.group(1) not in idx:
                idx[m.group(1)] = (os.path.basename(path), i + 1)
    return idx


def add_code_links(cache, repo):
    if not repo:
        return
    idx = code_index()
    for st_ in cache.values():
        for f in st_["fighters"]:
            if f["name"] in idx:
                fn, ln = idx[f["name"]]
                f["code"] = f"https://github.com/{repo}/blob/main/{fn}#L{ln}"


def freeze_finals(st, folder, now, cache):
    """At the finals deadline, lock in each league's winner (saved, so it never changes afterwards)."""
    import json
    fa = getattr(st, "finals_at", None)
    if not fa or folder is None:
        return None
    path = os.path.join(folder, "finals.json")
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:
            return None
    if now >= pd.Timestamp(fa) and len(cache) == 4:
        data = dict(at=str(pd.Timestamp(fa)), leagues={k: v["finals"] for k, v in cache.items()})
        json.dump(data, open(path, "w"), default=str)
        return data
    return None


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
