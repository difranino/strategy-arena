# ===================== STRATEGY ARENA — MEME COIN DEN (copy-trading, paper money) =====================
# One strategy: copy 5 of the best memecoin traders on Solana. When they buy, we buy; when they sell, we sell.
# Who: the top 5 of Kolscan's monthly KOL leaderboard (public wallets), picked on 12 Oct 2026.
# Data (free, no keys): their wallets' swaps from the public Solana blockchain, prices from DexScreener.
# Honest timing: the city only checks every 15-30 minutes, so every copy fills at the price WHEN WE SEE IT,
# not the trader's price. Paper money only: nothing is ever bought or sold for real.
import json, os, time
import urllib.request

START_CASH = 1000.0
FEE = 0.015            # 1.5% per buy or sell (swap fee + slippage on small memecoins)
COPY_PCT = 0.10        # each copied buy uses 10% of the account (at least $20, never more than the cash left)
MIN_TRADER_SOL = 0.5   # ignore the trader's tiny buys (dust, airdrops, tests)
MIN_LIQ = 10000.0      # skip tokens with less than $10k of liquidity (can't really be bought/sold)
MAX_TX_PER_WALLET = 25 # per update, newest first (very active wallets: the rest is skipped and counted)
RPC = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")

TRADERS = [  # (name, wallet) — Kolscan monthly leaderboard, 12 Oct 2026
    ("decu", "4vw54BmAogeRV3vPKWyFet5yf8DTLcREzdSzx4rw9Ud9"),
    ("Cented", "CyaE1VxvBrahnPWkqm5VsdCvyS2QmNht2UFrKJHga54o"),
    ("trunoest", "ardinRsN1mNYVeoJWTBsWeYeXvuR9UUDGMsCDKpb6AT"),
    ("theo", "Bi4rd5FH5bYEN8scZ7wevxNZyNmKHdaBcvewdPFxYdLt"),
    ("zeropnl", "4xY9T1Q7foJzJsJ6YZDSsfp9zkzeZsXnxd45SixduMmr"),
]
WSOL = "So11111111111111111111111111111111111111112"
STABLES = {"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}
SKIP_MINTS = {"So11111111111111111111111111111111111111112",   # wrapped SOL
              "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",   # USDC
              "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}   # USDT


def _post(payload, timeout=20):
    req = urllib.request.Request(RPC, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json",
                                                                                 "User-Agent": "StrategyArena"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def rpc(method, params, tries=3):
    for k in range(tries):
        try:
            js = _post({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
            if "error" in js:
                raise RuntimeError(js["error"].get("message", "rpc error"))
            return js.get("result")
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(1.5 * (k + 1))


def prices(mints):
    """{mint: dict(price, symbol, liq)} from DexScreener (best Solana pair by liquidity)."""
    out = {}
    mints = [m for m in dict.fromkeys(mints) if m]
    for i in range(0, len(mints), 30):
        chunk = mints[i:i + 30]
        try:
            req = urllib.request.Request("https://api.dexscreener.com/latest/dex/tokens/" + ",".join(chunk),
                                         headers={"User-Agent": "StrategyArena"})
            with urllib.request.urlopen(req, timeout=20) as r:
                js = json.loads(r.read())
        except Exception:
            continue
        for p in js.get("pairs") or []:
            if p.get("chainId") != "solana":
                continue
            m = (p.get("baseToken") or {}).get("address")
            if m not in chunk or not p.get("priceUsd"):
                continue
            liq = float((p.get("liquidity") or {}).get("usd") or 0)
            if m not in out or liq > out[m]["liq"]:
                out[m] = dict(price=float(p["priceUsd"]), symbol=(p.get("baseToken") or {}).get("symbol") or m[:4], liq=liq)
    return out


def swaps_in_tx(tx, wallet):
    """What the wallet bought/sold in one transaction: [(mint, delta_tokens, pre_tokens, sol_change, usd_change)]."""
    if not tx or (tx.get("meta") or {}).get("err"):
        return []
    meta = tx["meta"]
    keys = tx["transaction"]["message"]["accountKeys"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in keys]
    sol = 0.0
    if wallet in keys:
        i = keys.index(wallet)
        sol = (meta["postBalances"][i] - meta["preBalances"][i]) / 1e9

    def bal(rows):
        d = {}
        for b in rows or []:
            if b.get("owner") == wallet:
                d[b["mint"]] = d.get(b["mint"], 0.0) + float((b.get("uiTokenAmount") or {}).get("uiAmount") or 0.0)
        return d
    pre, post = bal(meta.get("preTokenBalances")), bal(meta.get("postTokenBalances"))
    # how much "money" moved: SOL (incl. wrapped SOL) and dollars (USDC/USDT)
    money = sol + (post.get(WSOL, 0) - pre.get(WSOL, 0))
    usd = sum(post.get(m, 0) - pre.get(m, 0) for m in STABLES)
    out = []
    for m in set(pre) | set(post):
        if m in SKIP_MINTS:
            continue
        dlt = post.get(m, 0.0) - pre.get(m, 0.0)
        if abs(dlt) > 0:
            out.append((m, dlt, pre.get(m, 0.0), money, usd))
    return out


def new_state(now):
    return dict(start=now, cash=START_CASH, positions={}, trades=[], feed=[], last_sig={}, equity=[], stats={},
                status="Just opened. Copying starts with the traders' NEXT trades.", skipped=0, prices={})


def _feed(S, t, kind, name, text, pnl=None):
    S["feed"].insert(0, dict(t=t, kind=kind, name=name, text=text, pnl=pnl))
    del S["feed"][150:]


def update(folder, now_ts=None, rpc_fn=None, price_fn=None):
    """One update: read the 5 wallets' new trades, copy them with paper money, mark everything to market."""
    rpc_fn, price_fn = rpc_fn or rpc, price_fn or prices
    now = now_ts or time.time()
    path = os.path.join(folder, "meme_state.json") if folder else None
    S = json.load(open(path)) if (path and os.path.exists(path)) else new_state(now)
    for n, _ in TRADERS:
        S["stats"].setdefault(n, dict(copies=0, wins=0, losses=0, realized=0.0, seen=0))
    signals, errors, skipped = [], [], 0
    for name, w in TRADERS:
        try:
            last = S["last_sig"].get(w)
            params = {"limit": 60}
            if last:
                params["until"] = last
            sigs = rpc_fn("getSignaturesForAddress", [w, params]) or []
            if not sigs:
                continue
            S["last_sig"][w] = sigs[0]["signature"]
            if not last:          # first look at this wallet: start copying from its next trade
                continue
            good = [s for s in sigs if not s.get("err")]
            skipped += max(0, len(good) - MAX_TX_PER_WALLET)
            for s in reversed(good[:MAX_TX_PER_WALLET]):   # oldest first
                try:
                    tx = rpc_fn("getTransaction", [s["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
                except Exception as e:
                    tx = None
                    errors.append(f"{name}: {str(e)[:60]}")
                for (mint, dlt, pre, money, usd) in swaps_in_tx(tx, w):
                    signals.append(dict(trader=name, mint=mint, delta=dlt, pre=pre, money=money, usd=usd,
                                        t=s.get("blockTime") or now))
                time.sleep(0.25)
        except Exception as e:
            errors.append(f"{name}: {str(e)[:60]}")
    held = [p["mint"] for p in S["positions"].values()]
    px = price_fn([g["mint"] for g in signals] + held)
    for m, v in px.items():
        S["prices"][m] = v
    t_now = now
    for g in sorted(signals, key=lambda x: x["t"]):
        name, m = g["trader"], g["mint"]
        info = S["prices"].get(m)
        S["stats"][name]["seen"] += 1
        late = max(0, int((t_now - g["t"]) / 60))
        key = f"{name}|{m}"
        if g["delta"] > 0:                                   # the trader BOUGHT
            if -g["money"] < MIN_TRADER_SOL and -g.get("usd", 0) < 50:   # tiny buy / airdrop
                continue
            paid = f"{-g['money']:.1f} SOL" if -g["money"] >= MIN_TRADER_SOL else f"${-g['usd']:,.0f}"
            if key in S["positions"]:
                continue                                      # already copying this one
            if not info or info["liq"] < MIN_LIQ:
                _feed(S, t_now, "info", name, f"bought {info['symbol'] if info else m[:6]} but it's too small to trade (liquidity under $10k). Skipped.")
                continue
            eq = equity(S)
            size = min(max(20.0, COPY_PCT * eq), S["cash"])
            if size < 20.0:
                _feed(S, t_now, "info", name, f"bought {info['symbol']} but we're out of cash. Skipped.")
                continue
            qty = size * (1 - FEE) / info["price"]
            S["cash"] -= size
            S["positions"][key] = dict(trader=name, mint=m, symbol=info["symbol"], qty=qty, cost=size,
                                       entry=info["price"], opened=t_now)
            S["stats"][name]["copies"] += 1
            S["trades"].insert(0, dict(t=t_now, trader=name, side="BUY", symbol=info["symbol"], usd=round(size, 2),
                                       price=info["price"], late_min=late))
            _feed(S, t_now, "long", name, f"COPIED a BUY: ${size:,.0f} of {info['symbol']} at ${info['price']:.6g} "
                                          f"({name} spent {paid}, we copied {late} min later).")
        elif key in S["positions"]:                           # the trader SOLD something we copied
            P = S["positions"][key]
            frac = 1.0 if g["pre"] <= 0 else min(1.0, -g["delta"] / g["pre"])
            if frac > 0.95:
                frac = 1.0
            price = info["price"] if info else P["entry"]
            qty = P["qty"] * frac
            proceeds = qty * price * (1 - FEE)
            cost = P["cost"] * frac
            pnl = proceeds - cost
            S["cash"] += proceeds
            P["qty"] -= qty
            P["cost"] -= cost
            st = S["stats"][name]
            st["realized"] += pnl
            st["wins" if pnl > 0 else "losses"] += 1
            S["trades"].insert(0, dict(t=t_now, trader=name, side="SELL", symbol=P["symbol"], usd=round(proceeds, 2),
                                       price=price, pnl=round(pnl, 2), late_min=late))
            _feed(S, t_now, "win" if pnl > 0 else "loss", name,
                  f"COPIED a SELL: sold {frac:.0%} of our {P['symbol']} at ${price:.6g} for {'+' if pnl >= 0 else '−'}${abs(pnl):,.2f} "
                  f"({late} min after {name}).", pnl)
            if frac >= 1.0 or P["qty"] <= 0:
                del S["positions"][key]
    del S["trades"][300:]
    S["skipped"] = S.get("skipped", 0) + skipped
    eq = equity(S)
    S["equity"].append([t_now, round(eq, 2)])
    S["equity"] = S["equity"][-3000:]
    errors = list(dict.fromkeys(errors))[:5]
    S["status"] = ("Some data sources didn't answer this time: " + "; ".join(errors)) if errors else "OK"
    S["updated"] = t_now
    if path:
        json.dump(S, open(path, "w"))
    return S


def equity(S):
    return S["cash"] + sum(p["qty"] * (S["prices"].get(p["mint"], {}).get("price", p["entry"])) for p in S["positions"].values())


def _uk(t):
    import pandas as pd
    return pd.Timestamp(t, unit="s", tz="UTC").tz_convert("Europe/London").strftime("%a %H:%M")


def view(S):
    """What the website shows."""
    if not S:
        return None
    eq = equity(S)
    pos = []
    for p in S["positions"].values():
        price = S["prices"].get(p["mint"], {}).get("price", p["entry"])
        val = p["qty"] * price
        pos.append(dict(trader=p["trader"], symbol=p["symbol"], mint=p["mint"], value=round(val, 2), cost=round(p["cost"], 2),
                        pnl=round(val - p["cost"], 2), opened=_uk(p["opened"])))
    pos.sort(key=lambda x: -x["value"])
    traders = []
    for n, w in TRADERS:
        st = S["stats"].get(n, {})
        op = [x for x in pos if x["trader"] == n]
        unreal = sum(x["pnl"] for x in op)
        traders.append(dict(name=n, wallet=w, copies=st.get("copies", 0), wins=st.get("wins", 0), losses=st.get("losses", 0),
                            realized=round(st.get("realized", 0.0), 2), open_pnl=round(unreal, 2),
                            pnl=round(st.get("realized", 0.0) + unreal, 2), open=len(op), seen=st.get("seen", 0)))
    traders.sort(key=lambda x: -x["pnl"])
    day_ago = [v for t, v in S["equity"] if t <= S["equity"][-1][0] - 86400] if S["equity"] else []
    return dict(start=S["start"], start_cash=START_CASH, equity=round(eq, 2), cash=round(S["cash"], 2), pnl=round(eq - START_CASH, 2),
                today=round(eq - (day_ago[-1] if day_ago else START_CASH), 2), positions=pos[:40], traders=traders,
                trades=[dict(x, t=_uk(x["t"])) for x in S["trades"][:40]], feed=[dict(x, t=_uk(x["t"])) for x in S["feed"][:60]], curve=[v for _, v in S["equity"][-300:]], status=S.get("status"),
                updated=_uk(S["updated"]) if S.get("updated") else None, started=_uk(S["start"]), skipped=S.get("skipped", 0),
                rules=dict(copy_pct=COPY_PCT, fee=FEE, min_sol=MIN_TRADER_SOL, min_liq=MIN_LIQ))
