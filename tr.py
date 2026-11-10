"""Thin wrapper around the treg CLI. Every call's charge is logged to <run dir>/costs.csv.

Auth: the treg CLI reads TREG_TOKEN from the environment (cloud) or its own login (laptop).
Run dir: LEADS_RUN_DIR env var, default ./run
"""
import csv
import json
import os
import re
import subprocess
import time

RUN_DIR = os.environ.get("LEADS_RUN_DIR", os.path.join(os.getcwd(), "run"))
COSTS = os.path.join(RUN_DIR, "costs.csv")
CURRENT = {"service": "setup"}  # set CURRENT["service"] = "01" before a service's calls
MAX_CALL_COST = 0.05            # never pay more than this for one call


def _log(endpoint, cost, note):
    os.makedirs(RUN_DIR, exist_ok=True)
    new = not os.path.exists(COSTS)
    with open(COSTS, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "service", "endpoint", "usd", "note"])
        w.writerow([time.strftime("%H:%M:%S"), CURRENT["service"], endpoint, cost, note[:100]])


def call(endpoint, data=None, max_cost=MAX_CALL_COST, headers=None, note="", timeout=120, retries=1):
    """POST to a treg endpoint. Returns parsed JSON, or {"_error": "..."} (never raises)."""
    max_cost = min(max_cost, MAX_CALL_COST)
    cmd = ["treg", "call", endpoint, "--method", "POST", "--header", f"X-Treg-Route-Max-Cost: {max_cost}"]
    for h in headers or []:
        cmd += ["--header", h]
    if data is not None:
        cmd += ["--data", json.dumps(data)]
    for attempt in range(retries + 1):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            _log(endpoint, 0.0, "timeout " + (note or ""))
            if attempt < retries:
                continue
            return {"_error": "timeout"}
        m = re.search(r"charged \$([0-9.]+)", p.stderr)
        _log(endpoint, float(m.group(1)) if m else 0.0, note or json.dumps(data or {}))
        if p.returncode != 0:
            return {"_error": (p.stderr or p.stdout)[:300]}
        try:
            return json.loads(p.stdout)
        except Exception:
            return {"_error": "non-json: " + p.stdout[:200]}
    return {"_error": "unknown"}


def spend(service=None):
    """Total logged spend, optionally for one service."""
    if not os.path.exists(COSTS):
        return 0.0
    with open(COSTS) as f:
        return sum(float(r["usd"]) for r in csv.DictReader(f) if service is None or r["service"] == service)
