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
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
ids = [k for k, v in services.SERVICES.items() if v.get("active")]
# slowest services first so they overlap with fast ones
order = sorted(ids, key=lambda k: k not in ("13", "05", "11", "01"))
queue = list(order)
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
print("finished", len(order), "services")
