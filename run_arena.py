"""Strategy City: one run = download the latest bars, replay every season, write the website.
GitHub runs this every 15 minutes (see .github/workflows/arena.yml)."""
import json, os, sys, time
import pandas as pd
import arena_live as AL

state_dir = sys.argv[1] if len(sys.argv) > 1 else "state"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "site"
os.makedirs(state_dir, exist_ok=True)
os.makedirs(out_dir, exist_ok=True)

cfg = json.load(open("settings.json")) if os.path.exists("settings.json") else {}
st = AL.Settings(**cfg)
t0 = time.time()
html, cache, errs = AL.build_all(st, state_dir, pd.Timestamp.now(tz="America/New_York"), reload_sec=300)
banner = ""
if errs:
    print("Some leagues failed:", errs)
    banner = ("<div style='padding:8px;font:12px sans-serif;color:#ff8a8a'>Some leagues could not update this time: "
              + "; ".join(errs) + "</div>")
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Strategy City</title>
<meta name="robots" content="noindex">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏙️</text></svg>">
</head><body style="margin:0;background:#05070d;padding:10px">{banner}{html}
<p style="color:#5d6a8a;font:11px sans-serif;text-align:center">A testing lab, not trading advice.</p></body></html>"""
open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(page)
json.dump({k: v["meta"] for k, v in cache.items()}, open(os.path.join(out_dir, "status.json"), "w"), default=str)
print(f"Built {len(cache)} leagues in {time.time() - t0:.0f}s")
if not cache:
    sys.exit(1)
