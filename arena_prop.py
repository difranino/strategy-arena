# ===================== STRATEGY ARENA — PROP-FIRM ACCOUNTS (Nasdaq tower) =====================
# Every fighter trades its OWN prop-firm account:
#   EVALUATION  pass with 2 days that each close at +$1,500 or more (they don't have to be in a row)
#   FUNDED      a fresh $50,000 account after passing; the goal is at least $150 a day
#   OUT         the moment the balance falls $2,000 below its highest balance (open trades included)
# The bot's rules on top of the firm's rules:
#   LOT SIZE    max 3 NQ minis, fewer when it's close to the $2,000 limit
#   DAILY STOP  flat for the rest of the day after losing $600 in a day
#   DAILY GOAL  in evaluation, flat for the day once it is +$1,500 (locks in a passing day)
# Decisions use only what was known at a bar's close; forced exits fill at the next bar's open.
import numpy as np
import pandas as pd

PROP = dict(size=50000.0, dd=2000.0, eval_day=1500.0, eval_days=2, payday=150.0, daily_stop=600.0,
            max_lots=3, tiers=[(1500.0, 3), (1000.0, 2), (0.0, 1)], lock=False)


def lots_for(room, P):
    for lim, k in P["tiers"]:
        if room > lim:
            return min(k, P["max_lots"])
    return 1


def simulate(master, trades, opens, start_i, P, point_value, cost_rt, raw_lots, stop_at_payday=False, name=""):
    """Re-runs one fighter's raw trades (made at `raw_lots` contracts) through its prop account,
    starting flat at bar `start_i`. Returns the account P&L curve, the trades it really took
    (with lots), its open position, the account summary and the moments worth announcing."""
    n = len(master)
    o, c = master["open"].values, master["close"].values
    if start_i >= n:
        start_i = n - 1
    dates = master["date"].values
    idx = master.index
    pv, cost = point_value, cost_rt
    # positions the raw strategy took, from start_i on
    pos = []
    for r in trades.itertuples():
        e, x = int(r.entry_i), int(r.exit_i)
        if e >= start_i:
            pos.append(dict(e=e, x=x, side=int(r.side), entry=float(r.entry), exit=float(r.exit),
                            pnl1=float(r.pnl) / raw_lots, reason=r.exit_reason, in_dec=int(r.in_dec), out_dec=int(r.out_dec),
                            stop=getattr(r, "stop", None), tp=getattr(r, "target", None)))
        elif x >= start_i and r.exit_reason != "close":
            # already holding when the account opens: the account takes the same position at its first open
            px = float(o[start_i])
            pos.append(dict(e=start_i, x=x, side=int(r.side), entry=px, exit=float(r.exit),
                            pnl1=int(r.side) * (float(r.exit) - px) * point_value - cost_rt, reason=r.exit_reason,
                            in_dec=int(r.in_dec), out_dec=int(r.out_dec), stop=getattr(r, "stop", None), tp=getattr(r, "target", None)))
    for op in opens:
        ei = int(idx.get_indexer([op["entry_time"]])[0])
        if ei < start_i:
            ei, entry = start_i, float(o[start_i])
        else:
            entry = float(op["entry"])
        pos.append(dict(e=ei, x=None, side=int(op["side"]), entry=entry, exit=None, pnl1=None, reason=None,
                        in_dec=int(op["in_dec"]), out_dec=None, stop=op.get("stop"), tp=op.get("target")))
    by_entry = {}
    for p in pos:
        by_entry.setdefault(p["e"], []).append(p)

    size, dd = P["size"], P["dd"]
    eq = np.zeros(n)
    realized = 0.0
    ref = 0.0                       # realized+open P&L when the current account started
    peak = size
    phase, good_days, passes = "eval", 0, 0
    f_days = f_paydays = 0
    f_pnl = f_done = 0.0
    dead, dead_i, dead_day = False, None, None
    open_ = []                      # positions held now
    taken = []                      # trades really taken
    events = []
    halted, force_exit = False, False
    day_open = size
    new_funded = False
    cur_day = None
    last_bal = size
    eval_days_log = []

    def mtm(i):
        return sum(p["side"] * (c[i] - p["entry"]) * pv * p["k"] for p in open_)

    def close_pos(p, i, px, why, dec, at_close):
        nonlocal realized
        pnl = p["side"] * (px - p["entry"]) * pv * p["k"] - cost * p["k"]
        realized += pnl
        taken.append(dict(entry_i=p["e"], exit_i=i, side=p["side"], entry=p["entry"], exit=px, pnl=pnl, exit_reason=why,
                          in_dec=p["in_dec"], out_dec=dec, lots=p["k"], at_close=at_close))

    for i in range(start_i, n):
        d = dates[i]
        if d != cur_day:                                        # a new session starts
            cur_day = d
            if new_funded:
                ref = realized + mtm(i - 1) if i > 0 else realized
                peak, new_funded = size, False
            day_open = size + (realized + (mtm(i - 1) if i > 0 else 0.0)) - ref
            halted = False
        if dead:
            eq[i] = eq[i - 1]
            continue
        # exits that happen at this bar
        if force_exit:
            for p in list(open_):
                close_pos(p, i, o[i], p["force"], i - 1, False)
                open_.remove(p)
            force_exit = False
        for p in list(open_):
            if p["x"] is not None and p["x"] == i:
                pnl = p["pnl1"] * p["k"]
                realized += pnl
                taken.append(dict(entry_i=p["e"], exit_i=i, side=p["side"], entry=p["entry"], exit=p["exit"], pnl=pnl,
                                  exit_reason=p["reason"], in_dec=p["in_dec"], out_dec=p["out_dec"], lots=p["k"], at_close=p["reason"] == "close"))
                open_.remove(p)
        # entries at this bar's open, sized by the room left at the previous close
        if not halted:
            for p in by_entry.get(i, []):
                if p["x"] is not None and p["x"] < i:
                    continue
                room = last_bal - (peak - dd)
                p["k"] = lots_for(room, P)
                if p["x"] == i:                                  # in and out on the same bar
                    realized += p["pnl1"] * p["k"]
                    taken.append(dict(entry_i=p["e"], exit_i=i, side=p["side"], entry=p["entry"], exit=p["exit"], pnl=p["pnl1"] * p["k"],
                                      exit_reason=p["reason"], in_dec=p["in_dec"], out_dec=p["out_dec"], lots=p["k"], at_close=p["reason"] == "close"))
                else:
                    open_.append(p)
        bal = size + realized + mtm(i) - ref
        # the firm's rule: $2,000 below the highest balance = OUT
        floor = peak - dd
        if P.get("lock"):
            floor = min(floor, size)
        if bal <= floor:
            for p in list(open_):
                close_pos(p, i, c[i], "blown", i, True)
                open_.remove(p)
            bal = size + realized - ref
            dead, dead_i, dead_day = True, i, d
            eq[i] = realized
            events.append(dict(t=idx[i], kind="loss", name=name, pnl=None,
                               text=f"BLEW THE {'FUNDED' if phase == 'funded' else 'EVALUATION'} ACCOUNT: balance ${bal:,.0f} is $2,000+ below its best (${peak:,.0f}). OUT at the bell."))
            last_bal = bal
            continue
        peak = max(peak, bal)
        last_bal = bal
        eq[i] = realized + mtm(i)
        dp = bal - day_open
        last_of_day = (i == n - 1) or (dates[i + 1] != d)
        # the bot's own daily rules
        if not halted:
            why = None
            if dp <= -P["daily_stop"]:
                why = "daily_stop"
            elif phase == "eval" and dp >= P["eval_day"]:
                why = "daily_goal"
            elif phase == "funded" and stop_at_payday and dp >= P["payday"]:
                why = "payday"
            if why:
                halted = True
                if open_:
                    if last_of_day:
                        for p in list(open_):
                            close_pos(p, i, c[i], why, i, True)
                            open_.remove(p)
                        bal = size + realized - ref
                        eq[i] = realized
                    else:
                        for p in open_:
                            p["force"] = why
                        force_exit = True
                if why != "payday":
                    events.append(dict(t=idx[i], kind="info", name=name, pnl=None,
                                       text=(f"DAILY STOP: down ${-dp:,.0f} today, so it stops trading until tomorrow." if why == "daily_stop"
                                             else f"DAILY GOAL: +${dp:,.0f} today, a passing day for the evaluation. Done for the day.")))
        if last_of_day:
            complete = bool(master["last"].values[i])
            dp = bal - day_open
            if not complete:
                continue
            if phase == "eval":
                if dp >= P["eval_day"]:
                    good_days += 1
                    eval_days_log.append(str(d))
                    if good_days >= P["eval_days"]:
                        for p in list(open_):
                            close_pos(p, i, c[i], "passed", i, True)
                            open_.remove(p)
                        eq[i] = realized
                        passes += 1
                        phase, new_funded = "funded", True
                        events.append(dict(t=idx[i], kind="trophy", name=name, pnl=None,
                                           text=f"PASSED THE EVALUATION (2 days of +$1,500)! Gets a FUNDED ${size:,.0f} account from the next session."))
                    else:
                        events.append(dict(t=idx[i], kind="win", name=name, pnl=None,
                                           text=f"EVALUATION DAY {good_days} of {P['eval_days']} done: +${dp:,.0f} today."))
            else:
                f_days += 1
                f_done += dp
                f_paydays += dp >= P["payday"]
    # current account picture
    i_last = n - 1
    if new_funded:
        bal, peak_now = size, size
    else:
        bal, peak_now = last_bal, peak
    floor = peak_now - dd
    if P.get("lock"):
        floor = min(floor, size)
    if phase == "funded" and not new_funded and not dead:
        today_dp = bal - day_open
        f_pnl = f_done + (today_dp if not bool(master["last"].values[i_last]) else 0.0)
    else:
        f_pnl = f_done
    open_out = [dict(side=p["side"], entry=p["entry"], entry_i=p["e"], in_dec=p["in_dec"], lots=p["k"], stop=p.get("stop"),
                     target=p.get("tp"), upnl=p["side"] * (c[i_last] - p["entry"]) * pv * p["k"]) for p in open_]
    info = dict(phase=phase, balance=round(bal), peak=round(peak_now), floor=round(floor), room=round(bal - floor),
                good_days=good_days, need_days=P["eval_days"], passes=passes, funded_days=f_days, paydays=int(f_paydays),
                funded_pnl=round(f_pnl), funded_avg=round(f_done / f_days) if f_days else None, dead=dead,
                dead_day=str(dead_day) if dead_day is not None else None, fresh=new_funded,
                lots_now=lots_for(bal - floor, P), halted=halted and not dead, eval_days_log=eval_days_log)
    tk = pd.DataFrame(taken, columns=["entry_i", "exit_i", "side", "entry", "exit", "pnl", "exit_reason", "in_dec", "out_dec", "lots", "at_close"])
    return eq, tk, open_out, info, events, dead_day


def open_account(master, raw_trades, lots_raw, start_i, P, sizing, name, asset):
    """Runs the account from start_i and returns (equity Series, display trades with attrs['open'], info, events, dead_day)."""
    pv, cr = sizing["point_value"], sizing["cost_rt"]
    eq, tk, op, info, ev, dday = simulate(master, raw_trades, raw_trades.attrs.get("open", []), start_i, P, pv, cr, lots_raw, name=name)
    w = simulate(master, raw_trades, raw_trades.attrs.get("open", []), start_i, P, pv, cr, lots_raw, stop_at_payday=True, name=name)[3]
    info.update(whatif_days=w["funded_days"], whatif_paydays=w["paydays"], whatif_pnl=w["funded_pnl"], whatif_passes=w["passes"])
    idx = master.index
    if len(tk):
        tk["asset"] = asset
        tk["entry_time"] = idx[tk.entry_i.values.astype(int)]
        et = idx[tk.exit_i.values.astype(int)]
        tk["exit_time"] = et + pd.to_timedelta(np.where(tk.at_close.values.astype(bool), 15, 0), unit="min")
        tk = tk.sort_values(["exit_time", "entry_time"], kind="mergesort").reset_index(drop=True)
    else:
        tk = pd.DataFrame(columns=["asset", "entry_time", "exit_time", "side", "entry", "exit", "pnl", "exit_reason", "in_dec",
                                   "out_dec", "lots", "entry_i", "exit_i", "at_close"])
    tk.attrs["open"] = [dict(asset=asset, side=o["side"], entry=o["entry"], entry_time=idx[o["entry_i"]], stop=o["stop"],
                             target=o["target"], in_dec=o["in_dec"], upnl=o["upnl"], lots=o["lots"]) for o in op]
    return pd.Series(eq, index=idx), tk, info, ev, dday
