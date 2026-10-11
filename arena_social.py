# ===================== STRATEGY ARENA — HYPE (Reddit chatter + news headlines) =====================
# Free sources, no keys:
#   * Reddit / WallStreetBets mention counts from ApeWisdom (snapshots saved every run, so history builds up)
#   * News headlines from Yahoo Finance and Google News, scored positive/negative with VADER
# Everything is time-stamped and only used AFTER it was published, so no fighter sees the future.
import os, json, time, re
import numpy as np
import pandas as pd
from arena_core import condition, once_per_day, enter_exit, cross_up, cross_dn
from arena_strats import S

NY = "America/New_York"
FIN_WORDS = {  # finance words VADER doesn't know
    "beat": 1.5, "beats": 1.5, "surge": 2.0, "surges": 2.0, "soar": 2.2, "soars": 2.2, "jump": 1.5, "jumps": 1.5,
    "rally": 1.8, "rallies": 1.8, "upgrade": 2.0, "upgraded": 2.0, "outperform": 1.8, "record": 1.2, "bullish": 2.0,
    "buyback": 1.2, "raises": 1.0, "tops": 1.2, "miss": -1.5, "misses": -1.5, "plunge": -2.5, "plunges": -2.5,
    "tumble": -2.0, "tumbles": -2.0, "slump": -2.0, "slumps": -2.0, "downgrade": -2.0, "downgraded": -2.0,
    "bearish": -2.0, "lawsuit": -1.8, "probe": -1.5, "recall": -1.5, "selloff": -2.0, "sell-off": -2.0, "cuts": -1.0,
    "falls": -1.2, "drops": -1.2, "sinks": -1.8, "warning": -1.5, "layoffs": -1.2, "antitrust": -1.2,
}
_VADER = None


def _vader():
    global _VADER
    if _VADER is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _VADER = SentimentIntensityAnalyzer()
        _VADER.lexicon.update(FIN_WORDS)
    return _VADER


def _get(url, timeout=15):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (StrategyArena)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------- Reddit (ApeWisdom)
def fetch_reddit(folder, tickers, min_gap_min=14):
    path = os.path.join(folder, "reddit_snapshots.csv")
    old = pd.read_csv(path, parse_dates=["ts"]) if os.path.exists(path) else pd.DataFrame()
    if len(old):
        old["ts"] = pd.to_datetime(old["ts"], utc=True)
        if (pd.Timestamp.now(tz="UTC") - old["ts"].max()).total_seconds() < min_gap_min * 60:
            return old
    rows = []
    try:
        for page in range(1, 9):
            js = json.loads(_get(f"https://apewisdom.io/api/v1.0/filter/all-stocks/page/{page}"))
            for r in js.get("results", []):
                if r.get("ticker") in tickers:
                    rows.append(dict(ts=pd.Timestamp.now(tz="UTC"), ticker=r["ticker"], rank=r.get("rank"),
                                     mentions=r.get("mentions"), mentions_24h_ago=r.get("mentions_24h_ago"),
                                     upvotes=r.get("upvotes"), rank_24h_ago=r.get("rank_24h_ago")))
            if page >= int(js.get("pages", 1)):
                break
    except Exception as e:
        print(f"Reddit data unavailable right now ({e}).")
    new = pd.concat([old, pd.DataFrame(rows)], ignore_index=True) if rows else old
    if len(new):
        new.to_csv(path, index=False)
    return new


# ---------------------------------------------------------------- news headlines (Yahoo + Google News)
def _yahoo_news(t):
    import yfinance as yf
    out = []
    try:
        for it in (yf.Ticker(t).news or []):
            c = it.get("content", it)
            title = c.get("title")
            ts = c.get("pubDate") or c.get("providerPublishTime")
            if title and ts:
                ts = pd.to_datetime(ts, unit="s", utc=True) if isinstance(ts, (int, float)) else pd.to_datetime(ts, utc=True)
                out.append((ts, t, title, "Yahoo"))
    except Exception:
        pass
    return out


def _google_news(t, name):
    import xml.etree.ElementTree as ET
    out = []
    try:
        q = f"{t}+{name}+stock".replace(" ", "+")
        x = ET.fromstring(_get(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"))
        for item in x.iter("item"):
            title = (item.findtext("title") or "").strip()
            pub = item.findtext("pubDate")
            if title and pub:
                out.append((pd.to_datetime(pub, utc=True), t, re.sub(r"\s+-\s+[^-]+$", "", title), "Google News"))
    except Exception:
        pass
    return out


NAMES = {"NVDA": "Nvidia", "TSLA": "Tesla", "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon", "META": "Meta",
         "GOOGL": "Alphabet", "AMD": "AMD", "PLTR": "Palantir"}


def fetch_news(folder, tickers, min_gap_min=29):
    path = os.path.join(folder, "news_headlines.csv")
    stamp = os.path.join(folder, "news_last_fetch.txt")
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["ts", "ticker", "title", "source", "sent"])
    if len(old):
        old["ts"] = pd.to_datetime(old["ts"], utc=True)
    if os.path.exists(stamp):
        try:
            last = pd.Timestamp(open(stamp).read().strip())
            if (pd.Timestamp.now(tz="UTC") - last).total_seconds() < min_gap_min * 60:
                return old
        except Exception:
            pass
    rows = []
    for t in tickers:
        rows += _yahoo_news(t) + _google_news(t, NAMES.get(t, t))
    if rows:
        new = pd.DataFrame(rows, columns=["ts", "ticker", "title", "source"])
        try:
            v = _vader()
            new["sent"] = [v.polarity_scores(x)["compound"] for x in new.title]
        except Exception as e:
            print(f"Sentiment scorer unavailable ({e}).")
            new["sent"] = 0.0
        allr = pd.concat([old, new], ignore_index=True)
        allr["key"] = allr.ticker + "|" + allr.title.str.lower().str.slice(0, 90)
        allr = allr.sort_values("ts").drop_duplicates("key", keep="first").drop(columns="key")
        allr.to_csv(path, index=False)
        open(stamp, "w").write(str(pd.Timestamp.now(tz="UTC")))
        return allr
    return old


# ---------------------------------------------------------------- turn the chatter into bar-by-bar features
def add_social_cols(dfs, news, reddit):
    """For every bar, only uses headlines/snapshots stamped BEFORE that bar closed."""
    for a, d in dfs.items():
        close_t = (d.index + pd.Timedelta(minutes=15)).tz_convert("UTC")
        ct = close_t.values.astype("datetime64[ns]").astype(np.int64)
        nn = news[news.ticker == a] if len(news) else news
        if len(nn):
            ts = pd.to_datetime(nn.ts, utc=True).values.astype("datetime64[ns]").astype(np.int64)
            order = np.argsort(ts)
            ts, sv = ts[order], nn.sent.values.astype(float)[order]
            cs = np.concatenate([[0.0], np.cumsum(sv)])
            hr = 3600 * 10 ** 9
            def window(hours):
                hi = np.searchsorted(ts, ct, side="right")
                lo = np.searchsorted(ts, ct - hours * hr, side="right")
                cnt = hi - lo
                ssum = cs[hi] - cs[lo]
                return cnt, np.where(cnt > 0, ssum / np.maximum(cnt, 1), np.nan)
            d["news_n2h"], d["news_sent2h"] = window(2)
            d["news_n6h"], d["news_sent6h"] = window(6)
            d["news_n24h"], d["news_sent24h"] = window(24)
            d["news_n7d"], _ = window(24 * 7)
            d["news_buzz"] = d.news_n24h / np.maximum(d.news_n7d / 7.0, 0.5)
        else:
            for c in ("news_n2h", "news_n6h", "news_n24h", "news_n7d"):
                d[c] = 0
            for c in ("news_sent2h", "news_sent6h", "news_sent24h"):
                d[c] = np.nan
            d["news_buzz"] = np.nan
        rr = reddit[reddit.ticker == a].copy() if len(reddit) else reddit
        if len(rr):
            rr["ts"] = pd.to_datetime(rr.ts, utc=True)
            rr = rr.sort_values("ts")
            left = pd.DataFrame({"t": close_t})
            m = pd.merge_asof(left, rr.rename(columns={"ts": "t"}), on="t", direction="backward",
                              tolerance=pd.Timedelta(hours=3))
            d["rd_mentions"] = m.mentions.values.astype(float)
            d["rd_rank"] = m["rank"].values.astype(float)
            prev = m.mentions_24h_ago.astype(float).values
            d["rd_hype"] = d.rd_mentions / np.maximum(np.nan_to_num(prev, nan=0.0), 1.0)
            r24 = m.rank_24h_ago.astype(float).values
            d["rd_climb"] = np.where(r24 > 0, r24 - d.rd_rank, np.nan)
        else:
            d["rd_mentions"] = d["rd_rank"] = d["rd_hype"] = d["rd_climb"] = np.nan
    return dfs


def latest_headlines(news, n=12):
    if not len(news):
        return []
    x = news.sort_values("ts", ascending=False).head(n)
    return [dict(t=pd.Timestamp(r.ts).tz_convert("Europe/London").strftime("%a %H:%M"), asset=r.ticker,
                 title=str(r.title)[:140], sent=round(float(r.sent), 2), src=r.source) for r in x.itertuples()]


def reddit_board(reddit):
    if not len(reddit):
        return []
    last = reddit[reddit.ts == reddit.ts.max()].sort_values("rank")
    return [dict(asset=r.ticker, rank=int(r.rank), mentions=int(r.mentions or 0),
                 prev=int(r.mentions_24h_ago) if r.mentions_24h_ago == r.mentions_24h_ago and r.mentions_24h_ago is not None else None)
            for r in last.itertuples()]


# ---------------------------------------------------------------- hype fighters
def _f(d, col, fill=np.nan):
    return d[col].fillna(fill) if col in d else pd.Series(fill, index=d.index)


def roster():
    L = []
    L.append(S("News Buzz Momentum", "Hype",
               lambda d: enter_exit(d, (d.news_n2h >= 3) & (d.news_sent2h > 0.2) & (d.close > d.vwap), d.close < d.vwap,
                                    (d.news_n2h >= 3) & (d.news_sent2h < -0.2) & (d.close < d.vwap), d.close > d.vwap),
               stop=1.5, about="A burst of headlines with a clear mood, and price agreeing. Rides the story.",
               why_l="{news_n2h:.0f} headlines in 2 hours, mood {news_sent2h:+.2f} (positive), and price is above VWAP.",
               why_s="{news_n2h:.0f} headlines in 2 hours, mood {news_sent2h:+.2f} (negative), and price is below VWAP.",
               exit_l="Price crossed VWAP against the story.", watch="Waiting for a burst of headlines (3+ in 2 hours)."))
    L.append(S("Headline Mood Trend", "Hype",
               lambda d: enter_exit(d, (d.news_sent24h > 0.15) & (d.news_n24h >= 3) & cross_up(d.close, d.ema20), d.news_sent24h < 0.0,
                                    (d.news_sent24h < -0.15) & (d.news_n24h >= 3) & cross_dn(d.close, d.ema20), d.news_sent24h > 0.0),
               stop=2.0, about="Trades in the direction of the last 24 hours of news mood, entering on a trend signal.",
               why_l="Last 24h of news is positive ({news_sent24h:+.2f} over {news_n24h:.0f} headlines) and price turned up.",
               why_s="Last 24h of news is negative ({news_sent24h:+.2f} over {news_n24h:.0f} headlines) and price turned down.",
               exit_l="The news mood flipped.", watch="Watching the 24-hour news mood."))
    L.append(S("Bad News Bounce", "Hype",
               lambda d: enter_exit(d, (_f(d, "news_sent24h", 0) < -0.2) & (d.rsi14 < 30), d.rsi14 > 50),
               stop=1.5, about="Contrarian: when the news is ugly and the stock is oversold, the worst is often priced in.",
               why_l="News mood is grim ({news_sent24h:+.2f}) and RSI is {rsi14:.0f}. Betting the bad news is priced in.",
               exit_l="RSI recovered to 50.", watch="Waiting for bad news plus an oversold stock."))
    L.append(S("Reddit Hype Rider", "Hype",
               lambda d: enter_exit(d, (_f(d, "rd_hype", 0) > 1.5) & (_f(d, "rd_mentions", 0) >= 20) & (d.close > d.vwap), d.close < d.vwap),
               stop=1.5, about="Buys a stock when Reddit mentions jump 50%+ in a day and the price is confirming.",
               why_l="Reddit mentions up {rd_hype:.1f}x vs yesterday ({rd_mentions:.0f} mentions) and price above VWAP.",
               exit_l="Lost VWAP, so the hype is fading.", watch="Waiting for a Reddit mention spike."))
    L.append(S("Fade the Crowd", "Hype",
               lambda d: once_per_day(d, np.zeros(len(d), bool), (_f(d, "rd_rank", 99) <= 5) & (d.dayret > 0.03), start_k=2),
               stop=1.5, tp=1.5, about="When a stock is a top-5 Reddit favourite and already up 3%+, shorts the euphoria.",
               why_s="Reddit rank #{rd_rank:.0f} and already up {dayret:+.2%} today. Fading the crowd.",
               watch="Waiting for a top-5 Reddit stock that's up 3%+."))
    L.append(S("Hype + News Confluence", "Hype",
               lambda d: enter_exit(d, (_f(d, "rd_hype", 0) > 1.3) & (_f(d, "news_sent24h", 0) > 0.1) & (d.close > d.vwap), d.close < d.vwap),
               stop=1.5, about="Only buys when Reddit buzz and news mood point the same way.",
               why_l="Reddit buzz {rd_hype:.1f}x and positive news ({news_sent24h:+.2f}) agree, price above VWAP.",
               exit_l="Lost VWAP.", watch="Waiting for Reddit and the news to agree."))
    for s_ in L:
        s_["scope"] = "each"
    return L


def pool():
    L = []
    L.append(S("Reddit Rank Climber", "Hype",
               lambda d: enter_exit(d, (_f(d, "rd_climb", 0) >= 10) & (d.close > d.vwap), d.close < d.vwap),
               stop=1.5, about="Buys stocks climbing 10+ places up the Reddit rankings in a day.",
               why_l="Climbed {rd_climb:.0f} places on Reddit in 24h (now #{rd_rank:.0f}).", exit_l="Lost VWAP.",
               watch="Waiting for a fast Reddit climber."))
    L.append(S("Quiet Stock Breakout", "Hype",
               lambda d: enter_exit(d, (d.news_n24h == 0) & (d.close > d.dch20), d.close < d.dcl10),
               stop=1.5, about="Breakouts with no news behind them are often real buying. Trades those.",
               why_l="New 20-bar high with zero headlines in 24h. Quiet accumulation.", exit_l="Hit the 10-bar exit.",
               watch="Waiting for a no-news breakout."))
    L.append(S("Sentiment Flip", "Hype",
               lambda d: enter_exit(d, cross_up(_f(d, "news_sent6h", 0), 0.1) & (d.close > d.ema20), _f(d, "news_sent6h", 0) < -0.05,
                                    cross_dn(_f(d, "news_sent6h", 0), -0.1) & (d.close < d.ema20), _f(d, "news_sent6h", 0) > 0.05),
               stop=1.5, about="Trades the moment the 6-hour news mood flips from negative to positive (or back).",
               why_l="6h news mood flipped positive ({news_sent6h:+.2f}).", why_s="6h news mood flipped negative ({news_sent6h:+.2f}).",
               exit_l="The mood flipped back.", watch="Watching for a news mood flip."))
    L.append(S("Buzz Without Move", "Hype",
               lambda d: once_per_day(d, (_f(d, "news_buzz", 0) > 3) & (d.dayret.abs() < 0.005) & (d.close > d.orh1),
                                      (_f(d, "news_buzz", 0) > 3) & (d.dayret.abs() < 0.005) & (d.close < d.orl1), start_k=2),
               stop=1.5, about="Lots of news but the stock hasn't moved yet. Trades the first breakout.",
               why_l="3x the usual news flow but flat on the day, now breaking up.",
               why_s="3x the usual news flow but flat on the day, now breaking down.", watch="Waiting for heavy news on a flat stock."))
    for s_ in L:
        s_["scope"] = "each"
    return L
