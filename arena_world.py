# ===================== STRATEGY ARENA — WORLD NEWS & BIG NAMES (Stock Exchange tower) =====================
# Free source, no key: Google News RSS searches about Trump, the Fed, world events and the big CEOs.
# Honest timing: a headline only counts from the moment WE first saw it (or its publish time, if later),
# and it stays "fresh" for a window measured from its publish time. So the bots never trade on news early.
import os, re
import numpy as np
import pandas as pd
from arena_core import enter_exit, once_per_day
from arena_strats import S
import arena_social as SOC

# topic -> (search queries, which stocks it moves: "market" = all of them)
TOPICS = {
    "trump": (["Trump", "Trump tariffs", "Trump Truth Social post stocks", "White House economy"], "market"),
    "fed": (["Federal Reserve Powell", "interest rates Fed decision"], "market"),
    "world": (["war markets", "oil prices", "China trade talks", "sanctions stocks"], "market"),
    "musk": (["Elon Musk"], ["TSLA"]),
    "huang": (["Jensen Huang"], ["NVDA"]),
    "cook": (["Tim Cook Apple"], ["AAPL"]),
    "nadella": (["Satya Nadella"], ["MSFT"]),
    "zuck": (["Mark Zuckerberg"], ["META"]),
    "bezos": (["Andy Jassy Amazon", "Jeff Bezos"], ["AMZN"]),
    "pichai": (["Sundar Pichai"], ["GOOGL"]),
    "su": (["Lisa Su AMD"], ["AMD"]),
    "karp": (["Alex Karp Palantir"], ["PLTR"]),
    "altman": (["Sam Altman OpenAI"], ["MSFT", "NVDA"]),
}
LABEL = {"trump": "Trump", "fed": "Fed", "world": "World", "musk": "Musk", "huang": "Huang", "cook": "Cook",
         "nadella": "Nadella", "zuck": "Zuckerberg", "bezos": "Amazon", "pichai": "Pichai", "su": "Lisa Su",
         "karp": "Karp", "altman": "Altman"}
MACRO = ("trump", "fed", "world")
MACRO_WORDS = {"tariff": -1.6, "tariffs": -1.6, "sanction": -1.2, "sanctions": -1.2, "war": -1.6, "invasion": -2.0,
               "missile": -1.5, "strike": -1.0, "strikes": -1.0, "ceasefire": 1.6, "truce": 1.5, "deal": 1.0,
               "agreement": 1.0, "stimulus": 1.5, "dovish": 1.5, "hawkish": -1.5, "recession": -2.0, "inflation": -0.8,
               "shutdown": -1.3, "default": -1.8, "crash": -2.5, "pause": 0.5, "exemption": 1.2, "exemptions": 1.2}


def _scorer():
    v = SOC._vader()
    v.lexicon.update(MACRO_WORDS)
    return v


def _google(q):
    import xml.etree.ElementTree as ET
    out = []
    try:
        x = ET.fromstring(SOC._get(f"https://news.google.com/rss/search?q={q.replace(' ', '+')}+when:2d&hl=en-US&gl=US&ceid=US:en"))
        for item in x.iter("item"):
            title = (item.findtext("title") or "").strip()
            pub = item.findtext("pubDate")
            if title and pub:
                out.append((pd.to_datetime(pub, utc=True), re.sub(r"\s+-\s+[^-]+$", "", title)))
    except Exception:
        pass
    return out


def fetch_world(folder, min_gap_min=14, keep_days=45):
    """Saves every headline once, with when it was published and when we first saw it."""
    path = os.path.join(folder, "world_news.csv") if folder else None
    cols = ["pub", "seen", "topic", "title", "sent"]
    old = pd.read_csv(path) if (path and os.path.exists(path)) else pd.DataFrame(columns=cols)
    for c in ("pub", "seen"):
        old[c] = pd.to_datetime(old[c], utc=True)
    now = pd.Timestamp.now(tz="UTC")
    if len(old) and (now - old.seen.max()).total_seconds() < min_gap_min * 60:
        return old
    rows = []
    for topic, (queries, _) in TOPICS.items():
        for q in queries:
            for pub, title in _google(q):
                rows.append((min(pub, now), now, topic, title))
    if not rows:
        return old
    new = pd.DataFrame(rows, columns=["pub", "seen", "topic", "title"])
    try:
        v = _scorer()
        new["sent"] = [v.polarity_scores(t)["compound"] for t in new.title]
    except Exception as e:
        print(f"Sentiment scorer unavailable ({e}).")
        new["sent"] = 0.0
    allr = pd.concat([old, new], ignore_index=True)
    allr["key"] = allr.topic + "|" + allr.title.str.lower().str.slice(0, 90)
    allr = allr.sort_values("seen", kind="mergesort").drop_duplicates("key", keep="first").drop(columns="key")
    allr = allr[allr.pub >= now - pd.Timedelta(days=keep_days)]
    if path:
        allr.to_csv(path, index=False)
    return allr


def _window_feats(close_ns, start_ns, end_ns, vals):
    """For every bar close: how many headlines are 'live' (start <= close <= end) and their average score."""
    n = len(close_ns)
    cnt = np.zeros(n + 1)
    tot = np.zeros(n + 1)
    a = np.searchsorted(close_ns, start_ns, side="left")
    b = np.searchsorted(close_ns, end_ns, side="right")
    ok = a < b
    np.add.at(cnt, a[ok], 1)
    np.add.at(cnt, b[ok], -1)
    np.add.at(tot, a[ok], vals[ok])
    np.add.at(tot, b[ok], -vals[ok])
    c = np.cumsum(cnt)[:n]
    t = np.cumsum(tot)[:n]
    return c, np.where(c > 0, t / np.maximum(c, 1), np.nan)


def add_world_cols(dfs, world):
    hr = 3600 * 10 ** 9
    for a, d in dfs.items():
        close_ns = (d.index + pd.Timedelta(minutes=15)).tz_convert("UTC").values.astype("datetime64[ns]").astype(np.int64)
        feats = {}
        groups = {"trump": ["trump"], "macro": list(MACRO),
                  "boss": [k for k, (_, tk) in TOPICS.items() if tk != "market" and a in tk]}
        for g, topics in groups.items():
            w = world[world.topic.isin(topics)] if len(world) else world
            if len(w):
                pub = pd.to_datetime(w.pub, utc=True).values.astype("datetime64[ns]").astype(np.int64)
                seen = pd.to_datetime(w.seen, utc=True).values.astype("datetime64[ns]").astype(np.int64)
                start = np.maximum(pub, seen)
                sv = w.sent.values.astype(float)
                feats[g + "_n2h"], feats[g + "_sent2h"] = _window_feats(close_ns, start, pub + 2 * hr, sv)
                if g == "macro":
                    neg = sv <= -0.4
                    feats["macro_neg1h"], _ = _window_feats(close_ns, start[neg], pub[neg] + hr, sv[neg])
            else:
                feats[g + "_n2h"], feats[g + "_sent2h"] = np.zeros(len(d)), np.full(len(d), np.nan)
                if g == "macro":
                    feats["macro_neg1h"] = np.zeros(len(d))
        for k, v in feats.items():
            d[k] = v
    return dfs


def latest_world(world, n=25):
    if not len(world):
        return []
    x = world.sort_values("pub", ascending=False).head(n)
    return [dict(t=pd.Timestamp(r.pub).tz_convert("Europe/London").strftime("%a %H:%M"), asset=LABEL.get(r.topic, r.topic),
                 title=str(r.title)[:140], sent=round(float(r.sent), 2), src="Google News") for r in x.itertuples()]


def _f(d, col, fill=0.0):
    return d[col].fillna(fill) if col in d else pd.Series(fill, index=d.index)


def roster():
    """News traders for the Stock Exchange: they read the world, not the chart."""
    L = []
    L.append(S("Trump Tape Reader", "News",
               lambda d: enter_exit(d, (_f(d, "trump_n2h") >= 2) & (_f(d, "trump_sent2h") > 0.25) & (d.close > d.vwap),
                                    _f(d, "trump_sent2h") < 0,
                                    (_f(d, "trump_n2h") >= 2) & (_f(d, "trump_sent2h") < -0.25) & (d.close < d.vwap),
                                    _f(d, "trump_sent2h") > 0),
               stop=1.5, about="Reads the Trump / White House headlines. Good news for markets (deals, tariff pauses) = buy; "
                               "threats (new tariffs, fights) = short. Only if the price agrees.",
               why_l="{trump_n2h:.0f} fresh Trump headlines, mood {trump_sent2h:+.2f} (market-friendly), and price is above VWAP.",
               why_s="{trump_n2h:.0f} fresh Trump headlines, mood {trump_sent2h:+.2f} (market-scary), and price is below VWAP.",
               exit_l="The Trump news mood turned the other way.", watch="Watching Trump / White House headlines."))
    L.append(S("CEO Headline Rider", "News",
               lambda d: enter_exit(d, (_f(d, "boss_n2h") >= 1) & (_f(d, "boss_sent2h") > 0.3) & (d.close > d.dopen),
                                    d.close < d.vwap,
                                    (_f(d, "boss_n2h") >= 1) & (_f(d, "boss_sent2h") < -0.3) & (d.close < d.dopen),
                                    d.close > d.vwap),
               stop=1.5, about="When a big name moves (Musk for Tesla, Jensen Huang for Nvidia, Tim Cook for Apple…), "
                               "follows the headline if the stock is already moving that way.",
               why_l="Fresh headline about the company's big name, mood {boss_sent2h:+.2f}, and the stock is green today.",
               why_s="Fresh headline about the company's big name, mood {boss_sent2h:+.2f}, and the stock is red today.",
               exit_l="Price crossed VWAP against the story.", watch="Watching Musk, Huang, Cook, Nadella, Zuckerberg, Bezos/Jassy, Pichai, Lisa Su, Karp and Altman."))
    L.append(S("World Shock Fade", "News",
               lambda d: once_per_day(d, (_f(d, "macro_neg1h") >= 3) & (d.close < d.vwap_l2), np.zeros(len(d), bool), start_k=2),
               stop=1.5, tp=2.0, about="Contrarian: a burst of scary world headlines (war, tariffs, Fed) often makes stocks "
                                       "overshoot. Buys the panic once it's stretched far below VWAP.",
               why_l="{macro_neg1h:.0f} scary world headlines in the last hour and price is stretched far below VWAP. Buying the panic.",
               watch="Waiting for a burst of scary world headlines plus a stretched sell-off."))
    L.append(S("Risk-Off Rider", "News",
               lambda d: enter_exit(d, np.zeros(len(d), bool), np.zeros(len(d), bool),
                                    (_f(d, "macro_neg1h") >= 3) & (_f(d, "macro_sent2h") < -0.2) & (d.close < d.vwap),
                                    d.close > d.vwap),
               stop=1.5, about="The opposite bet: when scary world news piles up (war, tariffs, hawkish Fed), "
                               "shorts stocks already falling and rides the fear.",
               why_s="{macro_neg1h:.0f} scary world headlines in the last hour (mood {macro_sent2h:+.2f}) and price below VWAP. Riding the fear.",
               exit_l="Price got back above VWAP, so the fear is fading.", watch="Watching Trump, Fed and world headlines for a scare."))
    for s_ in L:
        s_["scope"] = "each"
    return L
