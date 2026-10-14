# ===================== STRATEGY ARENA — MEME COIN DEN (own strategy, paper money) =====================
# One strategy, "Meme Momentum Hunter", trading Solana memecoins with a $1,000 paper account.
# Every update it scans the trending Solana coins (GeckoTerminal, free, no key), filters out the obvious
# traps, and keeps ALL the money working: up to 5 coins at a time, cash split equally between free slots.
# Exits: -20% stop, +60% take profit, a 20% trailing stop once a coin is up 30%+, momentum dying, or 48 hours.
# Honest timing: the city updates every 15-30 minutes, so fills happen at the price WHEN WE SEE IT.
# Paper money only: nothing is ever bought or sold for real.
import calendar, json, os, time
import urllib.request

START_CASH = 1000.0
FEE = 0.015            # 1.5% per buy or sell (swap fee + slippage on memecoins)
MAX_COINS = 5
MIN_LIQ = 100_000.0    # pool liquidity
MIN_VOL24 = 500_000.0  # 24h volume
MIN_AGE_H = 24         # skip coins younger than a day (most rugs happen early)
MIN_FDV = 1_000_000.0
STOP = -0.20
TAKE = 0.60
TRAIL_ARM, TRAIL = 0.30, 0.20
MAX_HOLD_H = 48
SKIP_SYMBOLS = {"SOL", "WSOL", "USDC", "USDT", "JUP", "JTO", "PYTH", "RAY", "BONK", "WIF"}  # majors, not memecoin plays


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "StrategyArena", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def trending(now):
    """Trending Solana pools from GeckoTerminal -> list of candidate coins."""
    out = []
    for page in (1, 2):
        js = _get(f"https://api.geckoterminal.com/api/v2/networks/solana/trending_pools?page={page}")
        for p in js.get("data") or []:
            a = p.get("attributes") or {}
            base = (((p.get("relationships") or {}).get("base_token") or {}).get("data") or {}).get("id", "")
            mint = base.split("_", 1)[1] if "_" in base else base
            chg = a.get("price_change_percentage") or {}
            vol = a.get("volume_usd") or {}
            name = a.get("name") or ""
            try:
                created = calendar.timegm(time.strptime((a.get("pool_created_at") or "")[:19], "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                created = now
            out.append(dict(mint=mint, symbol=name.split("/")[0].strip()[:12], price=float(a.get("base_token_price_usd") or 0),
                            liq=float(a.get("reserve_in_usd") or 0), vol24=float(vol.get("h24") or 0),
                            fdv=float(a.get("fdv_usd") or a.get("market_cap_usd") or 0),
                            h1=float(chg.get("h1") or 0), h6=float(chg.get("h6") or 0), h24=float(chg.get("h24") or 0),
                            age_h=(now - created) / 3600))
        time.sleep(1.0)
    return out


def prices(mints):
    """{mint: price} for coins we hold (DexScreener, best Solana pair by liquidity)."""
    out = {}
    mints = [m for m in dict.fromkeys(mints) if m]
    for i in range(0, len(mints), 30):
        chunk = mints[i:i + 30]
        try:
            js = _get("https://api.dexscreener.com/latest/dex/tokens/" + ",".join(chunk))
        except Exception:
            continue
        best = {}
        for p in js.get("pairs") or []:
            m = (p.get("baseToken") or {}).get("address")
            if p.get("chainId") != "solana" or m not in chunk or not p.get("priceUsd"):
                continue
            liq = float((p.get("liquidity") or {}).get("usd") or 0)
            if m not in best or liq > best[m][1]:
                best[m] = (float(p["priceUsd"]), liq, float((p.get("priceChange") or {}).get("h1") or 0))
        for m, (px, liq, h1) in best.items():
            out[m] = dict(price=px, liq=liq, h1=h1)
    return out


def score(c):
    """Strong, steady momentum with real money behind it; avoids coins that already went vertical."""
    return c["h6"] * min(c["vol24"] / 1e6, 20)


def picks(cands):
    ok = [c for c in cands if c["mint"] and c["price"] > 0 and c["symbol"].upper() not in SKIP_SYMBOLS
          and c["liq"] >= MIN_LIQ and c["vol24"] >= MIN_VOL24 and c["fdv"] >= MIN_FDV and c["age_h"] >= MIN_AGE_H
          and 3 <= c["h1"] <= 40 and c["h6"] >= 10 and c["h24"] > 0]
    return sorted(ok, key=score, reverse=True)


def new_state(now):
    return dict(mode="own", start=now, cash=START_CASH, positions={}, trades=[], feed=[], equity=[], watch=[],
                closed=dict(n=0, wins=0, losses=0, realized=0.0), status="Just opened.", updated=now)


def _feed(S, t, kind, name, text, pnl=None):
    S["feed"].insert(0, dict(t=t, kind=kind, name=name, text=text, pnl=pnl))
    del S["feed"][150:]


def equity(S):
    return S["cash"] + sum(p["qty"] * p["last"] for p in S["positions"].values())


def update(folder, now_ts=None, trend_fn=None, price_fn=None):
    trend_fn, price_fn = trend_fn or trending, price_fn or prices
    now = now_ts or time.time()
    path = os.path.join(folder, "meme_state.json") if folder else None
    S = json.load(open(path)) if (path and os.path.exists(path)) else None
    if not S or S.get("mode") != "own":          # the old copy-trading account is retired; fresh $1,000
        S = new_state(now)
    errors = []
    # 1) mark what we hold
    if S["positions"]:
        try:
            px = price_fn(list(S["positions"]))
        except Exception as e:
            px, _ = {}, errors.append(f"prices: {str(e)[:60]}")
        for m, P in S["positions"].items():
            if m in px:
                P["last"], P["h1"] = px[m]["price"], px[m]["h1"]
                P["peak"] = max(P["peak"], P["last"])
    # 2) exits
    for m, P in list(S["positions"].items()):
        ch = P["last"] / P["entry"] - 1
        from_peak = P["last"] / P["peak"] - 1
        held_h = (now - P["opened"]) / 3600
        why = None
        if ch <= STOP:
            why = f"stop loss ({ch:+.0%})"
        elif ch >= TAKE:
            why = f"take profit ({ch:+.0%})"
        elif P["peak"] / P["entry"] - 1 >= TRAIL_ARM and from_peak <= -TRAIL:
            why = f"trailing stop: fell {from_peak:.0%} from its best"
        elif P.get("h1", 0) <= -12:
            why = f"momentum died ({P['h1']:+.0f}% in the last hour)"
        elif held_h >= MAX_HOLD_H:
            why = f"time's up after {held_h:.0f} hours"
        if why:
            proceeds = P["qty"] * P["last"] * (1 - FEE)
            pnl = proceeds - P["cost"]
            S["cash"] += proceeds
            c = S["closed"]
            c["n"] += 1
            c["realized"] += pnl
            c["wins" if pnl > 0 else "losses"] += 1
            S["trades"].insert(0, dict(t=now, side="SELL", symbol=P["symbol"], usd=round(proceeds, 2), price=P["last"], pnl=round(pnl, 2), why=why))
            _feed(S, now, "win" if pnl > 0 else "loss", P["symbol"],
                  f"SOLD for {'+' if pnl >= 0 else '−'}${abs(pnl):,.2f}: {why}.", pnl)
            del S["positions"][m]
    # 3) entries: fill the free slots with the best trending coins, splitting ALL the cash
    try:
        cands = trend_fn(now)
        ranked = picks(cands)
        S["watch"] = [dict(symbol=c["symbol"], mint=c["mint"], h1=c["h1"], h6=c["h6"], h24=c["h24"], liq=c["liq"], vol24=c["vol24"],
                           held=c["mint"] in S["positions"]) for c in ranked[:10]]
        new = [c for c in ranked if c["mint"] not in S["positions"]][:max(0, MAX_COINS - len(S["positions"]))]
        for k, c in enumerate(new):
            if S["cash"] < 20:
                break
            size = S["cash"] / (len(new) - k)          # ALL the cash, split equally between today's new picks
            qty = size * (1 - FEE) / c["price"]
            S["cash"] -= size
            S["positions"][c["mint"]] = dict(symbol=c["symbol"], mint=c["mint"], qty=qty, cost=size, entry=c["price"],
                                             last=c["price"], peak=c["price"], h1=c["h1"], opened=now)
            S["trades"].insert(0, dict(t=now, side="BUY", symbol=c["symbol"], usd=round(size, 2), price=c["price"], pnl=None,
                                       why=f"up {c['h1']:+.0f}% in 1h and {c['h6']:+.0f}% in 6h on ${c['vol24'] / 1e6:,.1f}M volume"))
            _feed(S, now, "long", c["symbol"], f"BOUGHT ${size:,.0f} at ${c['price']:.6g}: up {c['h1']:+.0f}% in 1 hour, "
                                               f"{c['h6']:+.0f}% in 6 hours, ${c['vol24'] / 1e6:,.1f}M traded today, ${c['liq'] / 1e3:,.0f}k liquidity.")
    except Exception as e:
        errors.append(f"trending list: {str(e)[:60]}")
    del S["trades"][300:]
    S["equity"].append([now, round(equity(S), 2)])
    S["equity"] = S["equity"][-3000:]
    S["status"] = ("Some data sources didn't answer this time: " + "; ".join(errors)) if errors else "OK"
    S["updated"] = now
    if path:
        json.dump(S, open(path, "w"))
    return S


def _uk(t):
    import pandas as pd
    return pd.Timestamp(t, unit="s", tz="UTC").tz_convert("Europe/London").strftime("%a %H:%M")


def view(S):
    if not S or S.get("mode") != "own":
        return None
    eq = equity(S)
    pos = [dict(symbol=p["symbol"], mint=p["mint"], value=round(p["qty"] * p["last"], 2), cost=round(p["cost"], 2),
                pnl=round(p["qty"] * p["last"] - p["cost"], 2), chg=round((p["last"] / p["entry"] - 1) * 100, 1),
                opened=_uk(p["opened"])) for p in S["positions"].values()]
    pos.sort(key=lambda x: -x["value"])
    day_ago = [v for t, v in S["equity"] if t <= S["equity"][-1][0] - 86400] if S["equity"] else []
    c = S["closed"]
    return dict(mode="own", start=S["start"], start_cash=START_CASH, equity=round(eq, 2), cash=round(S["cash"], 2),
                pnl=round(eq - START_CASH, 2), today=round(eq - (day_ago[-1] if day_ago else START_CASH), 2),
                positions=pos, closed=dict(n=c["n"], wins=c["wins"], losses=c["losses"], realized=round(c["realized"], 2)),
                trades=[dict(x, t=_uk(x["t"])) for x in S["trades"][:40]], feed=[dict(x, t=_uk(x["t"])) for x in S["feed"][:60]],
                watch=S.get("watch", []), curve=[v for _, v in S["equity"][-300:]], status=S.get("status"),
                updated=_uk(S["updated"]), started=_uk(S["start"]),
                rules=dict(max_coins=MAX_COINS, fee=FEE, stop=STOP, take=TAKE, trail_arm=TRAIL_ARM, trail=TRAIL, max_hold=MAX_HOLD_H,
                           min_liq=MIN_LIQ, min_vol=MIN_VOL24, min_age=MIN_AGE_H))
