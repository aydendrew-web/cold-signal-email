"""Run the lead finders for all active services in small waves (many at once overloaded treg and caused timeouts).
Usage: python run_finders.py --exclude /tmp/exclude.json --out /tmp/out [--wave 4] [--target 4] [--max-minutes 20]
Every service always writes /tmp/out/svc_<id>.json (partial results if it hit the time limit) and log_<id>.txt."""
import argparse
import os
import subprocess
import sys

import services

here = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--exclude", required=True)
ap.add_argument("--out", default="/tmp/out")
ap.add_argument("--wave", type=int, default=4)
ap.add_argument("--target", type=int, default=4)
ap.add_argument("--max-minutes", type=float, default=15)
ap.add_argument("--cap", type=int, default=0, help="total lead goal; the shortfall after tier A is filled with Tier C shards")
ap.add_argument("--tc-shards", type=int, default=8)
ap.add_argument("--tc-wave", type=int, default=4)
ap.add_argument("--skip-a", action="store_true", help="testing: skip tier A and go straight to Tier C")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
ids = [k for k, v in services.SERVICES.items() if v.get("active")]
# slowest services first so they overlap with fast ones
order = sorted(ids, key=lambda k: k not in ("13", "05", "11", "01"))
queue = [] if a.skip_a else list(order)
running = {}
while queue or running:
    while queue and len(running) < a.wave:
        s = queue.pop(0)
        log = open(f"{a.out}/log_{s}.txt", "w")
        running[s] = subprocess.Popen([sys.executable, os.path.join(here, "finder.py"), s, "--target", str(a.target), "--out", f"{a.out}/svc_{s}.json",
                                       "--exclude", a.exclude, "--max-minutes", str(a.max_minutes)], stdout=log, stderr=subprocess.STDOUT)
    for s, p in list(running.items()):
        try:
            p.wait(timeout=2)
            del running[s]
        except subprocess.TimeoutExpired:
            pass
print("tier A finished", len(order), "services")
if a.cap:
    import glob
    import json
    got = 0
    for f in glob.glob(f"{a.out}/svc_[0-9]*.json"):
        try:
            got += len(json.load(open(f)))
        except Exception:
            pass
    short = a.cap - got
    if short > 0:
        m = -(-short // a.tc_shards)
        print(f"tier A found {got}, shortfall {short}: running {a.tc_shards} Tier C shards of {m}")
        pending = list(range(a.tc_shards))
        procs = {}
        while pending or procs:
            while pending and len(procs) < a.tc_wave:
                k = pending.pop(0)
                log = open(f"{a.out}/log_tc_{k}.txt", "w")
                procs[k] = subprocess.Popen([sys.executable, os.path.join(here, "finder.py"), "11", "--tier-c", "--shard", str(k), "--shards", str(a.tc_shards),
                                             "--target", str(m), "--out", f"{a.out}/svc_tc_{k}.json", "--exclude", a.exclude,
                                             "--max-minutes", str(a.max_minutes)], stdout=log, stderr=subprocess.STDOUT)
            for k, p in list(procs.items()):
                try:
                    p.wait(timeout=2)
                    del procs[k]
                except subprocess.TimeoutExpired:
                    pass
        print("tier C finished")
