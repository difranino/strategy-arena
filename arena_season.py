# ===================== STRATEGY ARENA — arenas, seasons, knockouts and game state =====================
# Every run replays each season from its start date, so knockouts and new challengers are always
# decided the same way from the same data. Nothing is ever decided with future prices.
import warnings
import numpy as np
import pandas as pd
import arena_core as C
import arena_prop as PR

warnings.simplefilter("ignore", FutureWarning)

NY, UK = "America/New_York", "Europe/London"
CLASS = {"Breakout": "Striker", "Reversal": "Counter", "Trend": "Rider", "Momentum": "Sprinter",
         "Quant": "Brain", "Hype": "Hypebeast", "Benchmark": "Boss"}


class Cfg:
    def __init__(self, start, ko_per_day=3, qual_sessions=40, week_len=5, min_qual_sessions=15, grace=3, revive=None):
        self.start = pd.Timestamp(start).date()
        self.grace = grace  # sessions a fighter must have fought before it can be knocked out
        self.revive = {n: pd.Timestamp(d).date() for n, d in (revive or {}).items()}  # second chances
        self.ko_per_day, self.qual_sessions, self.week_len = ko_per_day, qual_sessions, week_len
        self.min_qual_sessions = min_qual_sessions
        self.protect, self.protect_from = set(), None  # Hall of Fame: podium fighters kept after the finals


class Arena:
    """One league: its assets, fighters, challenger pool, benchmark ("the Boss"), sizing and rules."""
    def __init__(self, key, title, icon, dfs, master, roster, pool, bench, cfg, sizing, market="rth",
                 crown_needs_qual=True, unit_label="", extra=None, pool_needs_qual=True, risk_limit=1000.0, monkeys=None,
                 prop=None):
        self.key, self.title, self.icon = key, title, icon
        self.dfs, self.master = dfs, master
        self.roster, self.pool, self.bench = roster, pool, bench
        self.cfg, self.sizing, self.market = cfg, sizing, market
        self.crown_needs_qual, self.unit_label = crown_needs_qual, unit_label
        self.extra = extra or {}
        self.pool_needs_qual = pool_needs_qual
        self.risk_limit = risk_limit
        self.monkeys = monkeys or []
        self.prop = prop  # prop-firm account rules (dict) or None


def _f(x, nd=2):
    if x is None:
        return None
    try:
        x = float(x)
    except Exception:
        return None
    if np.isnan(x):
        return None
    if np.isinf(x):
        return 999.0
    return round(x, nd)


def _money(x):
    return ("+" if x > 0 else "−" if x < 0 else "") + f"${abs(x):,.0f}"


def _uk(ts):
    return pd.Timestamp(ts).tz_convert(UK)


# ---------------------------------------------------------------- run one fighter on every asset
def run_fighter(A, s, cross_targets):
    parts, opens = [], []
    eq = pd.Series(0.0, index=A.master.index)
    assets = s.get("assets") or list(A.dfs)
    for a in assets:
        d = A.dfs[a]
        tgt = cross_targets.get(s["name"], {}).get(a) if s.get("scope") == "cross" else None
        if s.get("scope") == "cross" and tgt is None:
            continue
        tr = C.backtest(d, s, asset=a, tgt=tgt, **A.sizing)
        e = tr.attrs["equity"].reindex(A.master.index, method="ffill").fillna(0.0)
        eq = eq + e
        opens += tr.attrs["open"]
        tr.attrs = {}
        parts.append(tr)
    tr = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["asset", "entry_time", "exit_time", "side", "entry", "exit", "pnl", "exit_reason", "in_dec", "out_dec"])
    if len(tr):
        tr = tr.sort_values(["exit_time", "entry_time", "asset"], kind="mergesort").reset_index(drop=True)
    tr.attrs["equity"] = eq
    tr.attrs["open"] = opens
    return tr


def run_season(A, now=None):
    now = now or pd.Timestamp.now(tz=NY)
    cfg = A.cfg
    strats = {s["name"]: s for s in A.roster + A.pool + [A.bench]}
    # cross-asset fighters first (they add columns that reason templates use), then clear the row cache
    cross = {}
    for n, s in strats.items():
        if s.get("scope") == "cross":
            cross[n] = s["fn"](A.dfs)
    C._ROWS.clear()
    bt = {n: run_fighter(A, s, cross) for n, s in strats.items()}
    bt_raw = dict(bt)  # the strategy's own trades (qualifying always uses these)
    eq = {n: t.attrs["equity"] for n, t in bt.items()}
    monkey_bt = [run_fighter(A, mk, {}) for mk in A.monkeys]
    monkey_eq = [t.attrs["equity"] for t in monkey_bt]
    acct = {}

    m = A.master
    dates = np.array(m["date"].values)
    sessions = sorted(set(dates))
    sess_last_i = {d: int(np.where(dates == d)[0][-1]) for d in sessions}
    sess_first_i = {d: int(np.where(dates == d)[0][0]) for d in sessions}
    complete = {d: bool(m["last"].values[sess_last_i[d]]) for d in sessions}
    live = [d for d in sessions if d >= cfg.start]
    asset0 = list(A.dfs)[0]

    def start_account(n, day):
        """Prop leagues: a fighter trades its own account from `day`; its season P&L is that account."""
        if not A.prop or day is None or day not in sess_first_i:
            return
        e, tk, info, ev, dday = PR.open_account(m, bt_raw[n], A.sizing.get("contracts", 1), sess_first_i[day], A.prop,
                                                A.sizing, n, asset0)
        eq[n], bt[n] = e, tk
        acct[n] = dict(info=info, events=ev, dead_day=dday, start=day)

    def eq_end(name, d):
        return float(eq[name].values[sess_last_i[d]])

    def eq_before(name, d):
        i = sess_first_i[d] - 1
        return float(eq[name].values[i]) if i >= 0 else 0.0

    def qualify(name, upto):
        win = [d for d in sessions if d < upto][-cfg.qual_sessions:]
        if len(win) < cfg.min_qual_sessions:
            return dict(ok=False, sessions=len(win), net=None, h1=None, h2=None, trades=0, win=None, pf=None, sharpe=None, dd=None)
        tz = m.index.tz
        s0 = pd.Timestamp(win[0]).tz_localize(tz)
        mid = pd.Timestamp(win[len(win) // 2]).tz_localize(tz)
        end = pd.Timestamp(win[-1]).tz_localize(tz) + pd.Timedelta(days=1)
        t = bt_raw[name]
        a, b1, b2 = C.score(t, s0, end), C.score(t, s0, mid), C.score(t, mid, end)
        ok = a["trades"] >= 10 and b1["net"] > 0 and b2["net"] > 0 and (a["pf"] if a["pf"] == a["pf"] else 0) >= 1.1
        return dict(ok=bool(ok), sessions=len(win), net=_f(a["net"], 0), h1=_f(b1["net"], 0), h2=_f(b2["net"], 0),
                    trades=int(a["trades"]), win=_f(a["win"], 3), pf=_f(a["pf"]), sharpe=_f(a["sharpe"]), dd=_f(a["maxdd"], 0))

    members, events, trophies = {}, [], []
    season_on = len(live) > 0
    first_day = live[0] if season_on else cfg.start
    if A.prop and season_on:
        for s in A.roster:
            start_account(s["name"], first_day)
        start_account(A.bench["name"], first_day)
        monkey_eq = [pd.Series(PR.simulate(m, t, t.attrs.get("open", []), sess_first_i[first_day], A.prop, A.sizing["point_value"],
                                           A.sizing["cost_rt"], A.sizing.get("contracts", 1))[0], index=m.index) for t in monkey_bt]
    for s in A.roster:
        n = s["name"]
        jd = first_day
        if s.get("joins") and season_on:  # added mid-season: starts on its own date (waits in the lobby until then)
            j0 = pd.Timestamp(s["joins"]).date()
            if j0 > first_day:
                later = [x for x in sessions if x >= j0]
                jd = later[0] if later else None
        members[n] = dict(name=n, origin="original", status="active", joined=jd,
                          base=(eq_before(n, jd) if jd is not None else 0.0) if season_on else float(eq[n].values[-1]),
                          qual=qualify(n, jd or first_day), ko_day=None, ko_pnl=None)
    bname = A.bench["name"]
    bench_base = eq_before(bname, first_day) if season_on else float(eq[bname].values[-1])
    used = set(members)
    tz = m.index.tz
    close_off = pd.Timedelta(hours=16) if A.market == "rth" else pd.Timedelta(hours=24)

    done_days = [d for d in live if complete[d]]
    for di, d in enumerate(done_days):
        nxt = [x for x in sessions if x > d]
        nxt = nxt[0] if nxt else None
        act = [mm for mm in members.values() if mm["status"] == "active" and mm["joined"] is not None and mm["joined"] <= d]
        pnl = {mm["name"]: eq_end(mm["name"], d) - mm["base"] for mm in act}

        def last3(mm):
            fought = [x for x in sessions if mm["joined"] <= x <= d]
            return eq_end(mm["name"], d) - (eq_end(mm["name"], fought[-4]) if len(fought) >= 4 else mm["base"]), len(fought)

        # fair knockouts: only fighters that are losing overall AND over their last 3 sessions,
        # and that have fought at least `grace` sessions, can be knocked out
        cands = []
        for mm in act:
            l3, n_f = last3(mm)
            if cfg.protect_from is not None and d >= cfg.protect_from and mm["name"] in cfg.protect:
                continue  # Hall of Fame: kept running after the finals so we keep testing it
            if pnl[mm["name"]] <= 0 and l3 <= 0 and n_f >= cfg.grace:
                cands.append(mm)
        cands.sort(key=lambda mm: pnl[mm["name"]])
        kos = cands[:cfg.ko_per_day]
        if A.prop:  # prop league: the only way out is blowing the account
            kos = [mm for mm in act if mm["name"] in acct and acct[mm["name"]]["dead_day"] == d]
        t_close = pd.Timestamp(d).tz_localize(tz) + close_off
        for mm in kos:
            mm.update(status="ko", ko_day=d, ko_pnl=pnl[mm["name"]])
            ndays = len([x for x in sessions if mm["joined"] <= x <= d])
            events.append(dict(t=t_close, kind="ko", name=mm["name"], pnl=pnl[mm["name"]],
                               text=(f"OUT! Blew its prop account after {ndays} session(s) ({_money(pnl[mm['name']])}). Leaves the tower for good."
                                     if A.prop else f"KNOCKED OUT after {ndays} session(s) with {_money(pnl[mm['name']])}.")))
        if act and not kos and not A.prop:
            events.append(dict(t=t_close, kind="info", name="", pnl=None,
                               text="Nobody knocked out: no fighter was losing overall and over its last 3 sessions (new fighters get 3 sessions' grace)."))
        if kos:
            # waiting room: challengers never used yet, plus knocked-out fighters after a 5-session cooldown
            waiting = [s for s in A.pool if s["name"] not in used]
            for mm in ([] if A.prop else members.values()):  # prop league: blown accounts never come back
                if mm["status"] == "ko" and mm["ko_day"] != d and len([x for x in sessions if mm["ko_day"] < x <= d]) >= 5:
                    waiting.append(strats[mm["name"]])
            upto = nxt or (d + pd.Timedelta(days=1))
            q = [(s["name"], qualify(s["name"], upto)) for s in waiting]
            # qualified challengers first (best Sharpe); if not enough, the best of the rest come in "on trial"
            qual_ok = sorted([x for x in q if x[1]["ok"]], key=lambda x: -(x[1]["sharpe"] or -99))
            trial = sorted([x for x in q if not x[1]["ok"]], key=lambda x: -(x[1]["net"] if x[1]["net"] is not None else -1e9))
            ok = qual_ok + trial
            for n, qq in ok[:len(kos)]:
                used.add(n)
                back = n in members
                start_account(n, nxt)
                members[n] = dict(name=n, origin="challenger", status="active", joined=nxt, base=eq_end(n, d),
                                  qual=qq, ko_day=None, ko_pnl=None, comeback=back)
                events.append(dict(t=t_close + pd.Timedelta(minutes=1), kind="join", name=n, pnl=None,
                                   text=((f"COMEBACK! Re-qualified (Sharpe {qq['sharpe']}) and returns " if back else f"NEW CHALLENGER passed qualifying (Sharpe {qq['sharpe']}, {qq['trades']} trades) and enters ") if qq["ok"] else ("COMEBACK! Back from the graveyard, on trial. Enters " if back else "NEW CHALLENGER (unproven, on trial) enters ")) +
                                        f"{'next session' if nxt is None else pd.Timestamp(nxt).strftime('%a %d %b')}."))
            if len(ok) < len(kos):
                events.append(dict(t=t_close + pd.Timedelta(minutes=2), kind="info", name="", pnl=None,
                                   text=f"Only {min(len(ok), len(kos))} of {len(kos)} empty seats filled: no other challenger passed qualifying."))
        for rn, rday in cfg.revive.items():
            mm = members.get(rn)
            if nxt == rday and mm is not None and mm["status"] == "ko":
                start_account(rn, nxt)
                members[rn] = dict(name=rn, origin="challenger", status="active", joined=nxt, base=eq_end(rn, d),
                                   qual=qualify(rn, nxt), ko_day=None, ko_pnl=None, comeback=True)
                events.append(dict(t=t_close + pd.Timedelta(minutes=4), kind="join", name=rn, pnl=None,
                                   text=f"SECOND CHANCE! Back from the cemetery for another go, starting {pd.Timestamp(nxt):%a %d %b} from $0."))
        if (di + 1) % cfg.week_len == 0:
            wk = (di + 1) // cfg.week_len
            wdays = done_days[di + 1 - cfg.week_len: di + 1]
            best, bp = None, 0.0
            for mm in members.values():
                if mm["status"] != "active" or mm["joined"] is None or mm["joined"] > d:
                    continue
                if A.crown_needs_qual and not mm["qual"]["ok"]:
                    continue
                st_day = max(wdays[0], mm["joined"])
                base = mm["base"] if st_day == mm["joined"] else eq_before(mm["name"], st_day)
                wp = eq_end(mm["name"], d) - base
                if wp > bp:
                    best, bp = mm["name"], wp
            bwk = eq_end(bname, d) - eq_before(bname, wdays[0])
            trophies.append(dict(week=wk, start=str(wdays[0]), end=str(d), name=best, pnl=_f(bp, 0), boss=_f(bwk, 0)))
            events.append(dict(t=t_close + pd.Timedelta(minutes=3), kind="trophy", name=best or "", pnl=bp if best else None,
                               text=(f"WEEK {wk} CHAMPION with {_money(bp)} for the week." if best else
                                     f"WEEK {wk}: no eligible fighter made money, so no trophy this week.")))
    for n, ac in acct.items():
        if n in members:
            events += ac["events"]
    return dict(strats=strats, bt=bt, eq=eq, members=members, events=events, trophies=trophies, sessions=sessions, acct=acct, bt_raw=bt_raw,
                live=live, done_days=done_days, complete=complete, sess_first_i=sess_first_i, sess_last_i=sess_last_i,
                bench=bname, bench_base=bench_base, now=now, qualify=qualify, monkey_eq=monkey_eq,
                monkey_base=[(float(e.values[sess_first_i[first_day] - 1]) if season_on and sess_first_i[first_day] > 0 else
                              (0.0 if season_on else float(e.values[-1]))) for e in monkey_eq])


def _is_live(A, now):
    if A.market == "crypto":
        return True
    n = now.tz_convert(NY)
    return n.dayofweek < 5 and (9, 30) <= (n.hour, n.minute) < (16, 0)


def _next_open(now):
    n = now.tz_convert(NY)
    d = n.normalize()
    for k in range(0, 8):
        day = d + pd.Timedelta(days=k)
        if day.dayofweek >= 5:
            continue
        op = day + pd.Timedelta(hours=9, minutes=30)
        if op > n:
            return op
    return d + pd.Timedelta(days=1, hours=9, minutes=30)


# ---------------------------------------------------------------- everything the hub shows for one arena
def game_state(A, S):
    cfg, now, m = A.cfg, S["now"], A.master
    cur_day = m["date"].values[-1]
    day_start_i = S["sess_first_i"][cur_day]
    day_start_ts = m.index[day_start_i]
    started = len(S["live"]) > 0
    in_session = _is_live(A, now) and (A.market == "crypto" or pd.Timestamp(cur_day) == pd.Timestamp(now.tz_convert(NY).date()))
    multi = len(A.dfs) > 1

    fighters, feed = [], []
    for n, mm in S["members"].items():
        s, t, eqs = S["strats"][n], S["bt"][n], S["eq"][n]
        active, pending = mm["status"] == "active", mm["joined"] is None
        w_in = lambda asset, side, dec, s=s: C.why_in(A.dfs[asset], s, side, dec)
        w_out = lambda r, s=s: C.why_out(A.dfs[r.asset], s, r.side, r.exit_reason, r.exit, r.out_dec)
        pnl = 0.0 if pending else (float(eqs.values[-1]) - mm["base"] if active else mm["ko_pnl"])
        j_ts = pd.Timestamp(mm["joined"]).tz_localize(m.index.tz) if mm["joined"] is not None else None
        tt = t[t.entry_time >= j_ts] if (j_ts is not None and len(t)) else t.iloc[0:0]
        if mm["ko_day"] is not None and len(tt):
            tt = tt[tt.exit_time < pd.Timestamp(mm["ko_day"]).tz_localize(m.index.tz) + pd.Timedelta(days=1)]
        wins, losses = int((tt.pnl > 0).sum()), int((tt.pnl <= 0).sum())
        spark = [0.0]
        pre_month = 0.0  # profit already banked before this calendar month started
        m0 = pd.Timestamp(cur_day).replace(day=1)
        if j_ts is not None:
            for d in S["sessions"]:
                if d < mm["joined"] or (mm["ko_day"] is not None and d > mm["ko_day"]):
                    continue
                spark.append(round(float(eqs.values[S["sess_last_i"][d]]) - mm["base"], 0))
                if pd.Timestamp(d) < m0:
                    pre_month = spark[-1]
        prop = S["acct"][n]["info"] if (A.prop and n in S.get("acct", {})) else None
        today_base = float(eqs.values[day_start_i - 1]) if day_start_i > 0 else 0.0
        if j_ts is not None and mm["joined"] == cur_day:
            today_base = mm["base"]
        today_pnl = float(eqs.values[-1]) - today_base if (active and not pending and mm["joined"] <= cur_day) else 0.0
        opens = t.attrs["open"] if (active and not pending) else []
        today_tr = t[(t.entry_time >= day_start_ts) | (t.exit_time >= day_start_ts)] if len(t) else t
        if j_ts is not None and len(today_tr):
            today_tr = today_tr[today_tr.entry_time >= j_ts]
        # what it's doing right now, and why
        if pending:
            pos, thought = "waiting", "Warming up in the tunnel. Enters at the next session."
        elif not active:
            pos, thought = "ko", f"Knocked out on {pd.Timestamp(mm['ko_day']):%a %d %b}."
        elif opens:
            o0 = opens[0]
            pos = ("long" if o0["side"] > 0 else "short") if len(opens) == 1 else "multi"
            lead = (o0["asset"] + ": ") if multi else ""
            thought = lead + w_in(o0["asset"], o0["side"], o0["in_dec"])
            if len(opens) > 1:
                thought += f" (+{len(opens) - 1} more open)"
        else:
            pos = "flat"
            last_t = today_tr.iloc[-1] if len(today_tr) else None
            if not in_session:
                thought = "Resting until the next session. Game plan: " + s["about"]
            else:
                a0 = list(A.dfs)[0]
                w = C.say(s.get("watch"), C.row_at(A.dfs[a0], len(A.dfs[a0]) - 1), s["about"])
                if multi:
                    w = f"Scanning {len(A.dfs)} {A.unit_label}. " + ((a0 + ": ") if "{" in (s.get("watch") or "") else "") + w
                look = w
                thought = ((((last_t.asset + ": ") if multi else "") + w_out(last_t) + " Now: ") if last_t is not None else "") + look
        if (active and not pending) or mm["ko_day"] == cur_day:
            for tr_ in today_tr.itertuples():
                tag = (tr_.asset + " · ") if multi else ""
                if tr_.entry_time >= day_start_ts:
                    feed.append(dict(t=tr_.entry_time, kind="long" if tr_.side > 0 else "short", name=n,
                                     text=f"{tag}{'BUYS' if tr_.side > 0 else 'SELLS SHORT'} at {tr_.entry:,.2f}. {w_in(tr_.asset, tr_.side, tr_.in_dec)}", pnl=None))
                feed.append(dict(t=tr_.exit_time, kind="win" if tr_.pnl > 0 else "loss", name=n,
                                 text=f"{tag}EXITS {_money(tr_.pnl)}. {w_out(tr_)}", pnl=float(tr_.pnl)))
            for o in opens:
                if o["entry_time"] >= day_start_ts:
                    tag = (o["asset"] + " · ") if multi else ""
                    feed.append(dict(t=o["entry_time"], kind="long" if o["side"] > 0 else "short", name=n,
                                     text=f"{tag}{'BUYS' if o['side'] > 0 else 'SELLS SHORT'} at {o['entry']:,.2f}. {w_in(o['asset'], o['side'], o['in_dec'])}", pnl=None))
        marks = []
        for tr_ in today_tr.itertuples():
            marks.append(dict(a=tr_.asset, t=_uk(tr_.entry_time).strftime("%H:%M"), px=_f(tr_.entry), k="in", side=int(tr_.side)))
            et = tr_.exit_time - (pd.Timedelta(minutes=15) if tr_.exit_reason == "close" else pd.Timedelta(0))
            marks.append(dict(a=tr_.asset, t=_uk(et).strftime("%H:%M"), px=_f(tr_.exit), k="out", side=int(tr_.side), pnl=_f(tr_.pnl, 0)))
        for o in opens:
            if o["entry_time"] >= day_start_ts:
                marks.append(dict(a=o["asset"], t=_uk(o["entry_time"]).strftime("%H:%M"), px=_f(o["entry"]), k="in", side=int(o["side"])))
        trades_list = [dict(when=_uk(r.entry_time).strftime("%a %d %b %H:%M"), asset=r.asset, side="Long" if r.side > 0 else "Short",
                            entry=_f(r.entry), exit=_f(r.exit), pnl=_f(r.pnl, 0), lots=(int(r.lots) if hasattr(r, "lots") and r.lots == r.lots else None), why=w_in(r.asset, r.side, r.in_dec), out=w_out(r))
                       for r in tt.tail(15).iloc[::-1].itertuples()]
        open_list = [dict(asset=o["asset"], side="Long" if o["side"] > 0 else "Short", entry=_f(o["entry"]), lots=o.get("lots"),
                          stop=_f(o["stop"]), target=_f(o["target"]), upnl=_f(o["upnl"], 0),
                          since=_uk(o["entry_time"]).strftime("%a %H:%M"), why=w_in(o["asset"], o["side"], o["in_dec"])) for o in opens]
        days_in = len([d for d in S["done_days"] if j_ts is not None and d >= mm["joined"] and (mm["ko_day"] is None or d <= mm["ko_day"])])
        fighters.append(dict(**day_stats(spark), rules=rulebook(s, A), name=n, family=s["family"], cls=CLASS.get(s["family"], s["family"]), about=s["about"],
                             origin=mm["origin"], status=("entering" if pending else mm["status"]),
                             pnl=_f(pnl, 0), today=_f(today_pnl, 0), month=_f(pnl - pre_month, 0), wins=wins, losses=losses, level=1 + days_in,
                             qualified=bool(mm["qual"]["ok"]), qual=mm["qual"], pos=pos, thought=thought, opens=open_list,
                             spark=spark, marks=marks, trades=trades_list, joined=str(mm["joined"]) if mm["joined"] else None,
                             ko_day=str(mm["ko_day"]) if mm["ko_day"] else None, prop=prop))
    act = [f for f in fighters if f["status"] == "active"]
    for f in fighters:
        sp = f["spark"]
        f["fought"] = max(0, len(sp) - 1)
        f["last3"] = (sp[-1] - sp[-4]) if len(sp) >= 4 else (sp[-1] if sp else 0.0)
        f["grace_left"] = max(0, cfg.grace - f["fought"]) if (f["status"] == "active" and not A.prop) else 0
    elig = [f for f in act if (f["pnl"] or 0) <= 0 and f["last3"] <= 0 and f["fought"] >= cfg.grace]
    elig.sort(key=lambda f: f["pnl"] or 0)
    danger = {f["name"] for f in elig[:cfg.ko_per_day]} if started else set()
    if A.prop:  # danger = blown today, or within $500 of the limit
        danger = {f["name"] for f in act if f.get("prop") and (f["prop"]["dead"] or f["prop"]["room"] <= 500)}
    for f in fighters:
        f["danger"] = f["name"] in danger
        f["safe"] = f["status"] == "active" and ((f["pnl"] or 0) > 0 or f["last3"] > 0)
        f["immune"] = f["grace_left"] > 0
    beq = S["eq"][S["bench"]]
    boss = dict(name=S["bench"], pnl=_f(float(beq.values[-1]) - S["bench_base"], 0),
                today=_f(float(beq.values[-1]) - (float(beq.values[day_start_i - 1]) if day_start_i > 0 else 0.0), 0))
    feed += S["events"]
    feed.sort(key=lambda e: e["t"], reverse=True)
    feed_out = [dict(t=_uk(e["t"]).strftime("%a %H:%M"), kind=e["kind"], name=e["name"], text=e["text"],
                     pnl=_f(e["pnl"], 0) if e.get("pnl") is not None else None) for e in feed[:150]]
    upto = (pd.Timestamp(cur_day) + pd.Timedelta(days=1)).date()
    queue = []
    for s in A.pool:
        if s["name"] in S["members"]:
            continue
        queue.append(dict(name=s["name"], cls=CLASS.get(s["family"], s["family"]), about=s["about"], qual=S["qualify"](s["name"], upto)))
    queue.sort(key=lambda q: (not q["qual"]["ok"], -(q["qual"]["sharpe"] or -99)))
    candles = {}
    for a, d in A.dfs.items():
        td = d[d["date"] == cur_day]
        candles[a] = [[_uk(ts).strftime("%H:%M"), _f(r.open), _f(r.high), _f(r.low), _f(r.close), _f(r.vwap)] for ts, r in td.iterrows()]
    leader = None
    alive = lambda f: not (f.get("prop") or {}).get("dead")
    pool_l = [f for f in act if (f["pnl"] or 0) > 0 and (f["qualified"] or not A.crown_needs_qual) and alive(f)]
    if pool_l:
        leader = max(pool_l, key=lambda f: f["pnl"])["name"]
    top_raw = max(act, key=lambda f: f["pnl"] or 0)["name"] if act else None
    tick = []
    for a, d in A.dfs.items():
        pc = d.pdc.iloc[-1]
        price = float(d.close.iloc[-1])
        pc = float(pc) if pc == pc else price
        tick.append(dict(a=a, price=_f(price), chg_pct=_f((price / pc - 1) * 100)))
    nxt_open = _next_open(now)
    if A.market == "crypto":
        ko_time = "00:00 UK (midnight)"
    else:
        ko_time = _uk(pd.Timestamp(now.tz_convert(NY).date()).tz_localize(NY) + pd.Timedelta(hours=16)).strftime("%H:%M") + " UK"
    meta = dict(key=A.key, title=A.title, icon=A.icon, live=bool(in_session), started=started, multi=multi,
                last_bar=_uk(m.index[-1] + pd.Timedelta(minutes=15)).strftime("%a %d %b %H:%M"),
                updated=_uk(now).strftime("%H:%M:%S"), season_start=pd.Timestamp(cfg.start).strftime("%a %d %b"),
                day_n=len(S["live"]), week_n=(max(len(S["live"]) - 1, 0) // cfg.week_len) + 1 if started else 0,
                ko_per_day=cfg.ko_per_day, ko_time=ko_time, next_open=_uk(nxt_open).strftime("%a %d %b %H:%M"),
                n_active=len(act), n_ko=len([f for f in fighters if f["status"] == "ko"]), pool_left=len(queue),
                leader=leader, top_raw=top_raw, cur_day=pd.Timestamp(cur_day).strftime("%a %d %b"),
                crown_needs_qual=A.crown_needs_qual, sizing=A.extra.get("sizing_text", ""), units=A.unit_label,
                qual_sessions=cfg.qual_sessions, assets=list(A.dfs), tick=tick)
    fighters.sort(key=lambda f: ({"active": 0, "entering": 1, "ko": 2}[f["status"]], -(f["pnl"] or 0)))
    out = dict(meta=meta, fighters=fighters, boss=boss, feed=feed_out, queue=queue, trophies=S["trophies"], candles=candles)
    out.update({k: v for k, v in A.extra.items() if k in ("headlines", "reddit")})
    mk = [float(e.values[-1]) - b for e, b in zip(S["monkey_eq"], S["monkey_base"])] if started else [0.0] * len(S["monkey_eq"])
    out["monkeys"] = dict(n=len(mk), median=_f(float(np.median(mk)), 0) if mk else None,
                          p75=_f(float(np.percentile(mk, 75)), 0) if mk else None,
                          best=_f(max(mk), 0) if mk else None, worst=_f(min(mk), 0) if mk else None)
    out["meta"]["grace"] = cfg.grace
    if A.prop:
        ps = [f["prop"] for f in fighters if f["status"] == "active" and f.get("prop") and not f["prop"]["dead"]]
        out["prop"] = dict(rules=A.prop, n_eval=sum(p["phase"] == "eval" for p in ps), n_funded=sum(p["phase"] == "funded" for p in ps),
                           n_out=len([f for f in fighters if f["status"] == "ko"]) + len([f for f in act if f.get("prop") and f["prop"]["dead"]]),
                           passes=sum(p["passes"] for p in ps), boss=(S["acct"].get(S["bench"]) or {}).get("info"),
                           best_funded=max(((f["name"], f["prop"]["funded_pnl"]) for f in fighters
                                            if f["status"] == "active" and f.get("prop") and f["prop"]["funded_days"]),
                                           key=lambda x: x[1], default=None))
    out["finals"] = finals(out, A.crown_needs_qual, A.risk_limit, prop=bool(A.prop))
    return out




# ---------------------------------------------------------------- plain-English rulebook
import re as _re


def _plain(t):
    if not t:
        return ""
    t = _re.sub(r"\{[^}]*\}", "…", t)
    t = _re.sub(r"…\.", "…", t)
    t = _re.sub(r"\(\s*…\s*\)", "", t)
    t = _re.sub(r"\s+", " ", t).strip()
    return t


def rulebook(s, A):
    assets = ", ".join(a.replace("-USD", "") for a in A.dfs)
    out = [f"Trades: {assets} on 15-minute candles. {A.extra.get('sizing_text', '')}".strip()]
    if s.get("why_l"):
        out.append("Goes LONG when: " + _plain(s["why_l"]))
    if s.get("why_s"):
        out.append("Goes SHORT when: " + _plain(s["why_s"]))
    if s.get("exit_l"):
        out.append("Exits when: " + _plain(s["exit_l"]))
    if s.get("stop"):
        out.append(f"Protective stop: {s['stop']} × ATR(14) away from the entry price.")
    if s.get("tp"):
        out.append(f"Profit target: {s['tp']} × ATR(14) away from the entry price.")
    if s.get("intraday"):
        out.append("Always flat by the end of the session" + (" (midnight UK)." if A.market == "crypto" else " (closing bell)."))
    else:
        out.append("Can hold positions overnight.")
    out.append("Decides at the close of each 15-minute candle and enters at the next candle's open. Can trade again whenever its setup shows up.")
    if s.get("watch"):
        out.append("While waiting it watches for: " + _plain(s["watch"]))
    return out


def day_stats(spark):
    v = np.asarray(spark, float)
    if len(v) < 2:
        return dict(days_total=0, days_up=0, worst_day=0.0, max_dd=0.0)
    d = np.diff(v)
    dd = float(np.max(np.maximum.accumulate(v) - v))
    return dict(days_total=int(len(d)), days_up=int((d > 0).sum()), worst_day=float(d.min()), max_dd=dd)


FINAL_RISK_LIMIT = 1000.0  # worst single day must stay above -$1,000 (prop-firm style daily loss limit)


def finals(state, crown_needs_qual=True, risk_limit=FINAL_RISK_LIMIT, prop=False):
    """Who would win the league right now, and which checks each contender passes."""
    rows = []
    for f in state["fighters"]:
        if f["status"] != "active" or (f.get("prop") or {}).get("dead"):
            continue
        ch = dict(qualified=bool(f["qualified"] or not crown_needs_qual), profit=(f["pnl"] or 0) > 0,
                  consistent=f["days_total"] > 0 and f["days_up"] / f["days_total"] >= 0.5,
                  risk=f["worst_day"] > -risk_limit, trades=(f["wins"] + f["losses"]) >= 3,
                  monkeys=(state.get("monkeys", {}).get("p75") is None) or (f["pnl"] or 0) > state["monkeys"]["p75"])
        if prop:
            pr = f.get("prop") or {}
            ch["funded"] = bool(pr.get("passes", 0) > 0)
        rows.append(dict(name=f["name"], pnl=f["pnl"], checks=ch, passed=all(ch.values()), n_ok=sum(ch.values()),
                         beat_boss=(f["pnl"] or 0) > (state["boss"]["pnl"] or 0), days=f"{f['days_up']}/{f['days_total']}",
                         worst_day=round(f["worst_day"]), max_dd=round(f["max_dd"])))
    ok = sorted([r for r in rows if r["passed"]], key=lambda r: -(r["pnl"] or 0))
    close = sorted([r for r in rows if not r["passed"]], key=lambda r: (-r["n_ok"], -(r["pnl"] or 0)))
    # PODIUM: the best 3 of each league are kept. Ranked by how many finals checks they pass, then by profit.
    # Only fighters in profit can stand on it. Medal 1 is the champion only if it passes every check.
    podium = sorted([r for r in rows if r["checks"]["profit"]], key=lambda r: (-r["n_ok"], -(r["pnl"] or 0)))[:3]
    for i, r in enumerate(podium):
        r["medal"] = i + 1
    return dict(winner=ok[0] if ok else None, runners=ok[1:3], closest=close[:2], podium=podium, n_checks=7 if prop else 6,
                risk_limit=risk_limit, needs_qual=crown_needs_qual)
