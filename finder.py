"""Run one service end to end: discover candidates (stage 1), then find verified contacts (stage 2) within a budget.
Usage: python finder.py <service> [--target 4] [--out file.json] [--exclude file.json] [--contact-cap 0.6]
Writes {"leads": [...], "dropped": [...], "spend_usd": x}. A lead only appears if its email verified and its email passes the lint.
"""
import argparse
import json
import re
import sys
import time

import contact
import discover
import render_emails
import tr


def run(service, target=4, exclude=(), contact_cap=0.60, discover_limit=15, deadline=None, partial=None,
        tier_c=False, shard=0, shards=1, catchall_share=0.4):
    """deadline: epoch seconds after which no new contact lookups start. partial: list that receives each lead as found."""
    tr.CURRENT["service"] = service
    t0 = time.time()
    s0 = tr.spend(service)
    try:
        cands = discover.discover_tier_c(service, exclude=exclude, limit=max(target * 4, 12), shard=shard, shards=shards) if tier_c else discover.discover(service, exclude=exclude, limit=discover_limit)
    except Exception as e:  # a broken source must not kill the run
        return {"leads": [], "dropped": [{"reason": "discovery error " + repr(e)[:120]}], "spend_usd": tr.spend(service) - s0}
    s_disc = tr.spend(service) - s0
    out, dropped, seen = [], [], set()
    queue = []
    for c in sorted(cands, key=lambda c: -c.get("score", 0)):
        if c["domain"] not in seen:
            seen.add(c["domain"])
            queue.append(c)
    i = 0
    catchall_max = max(1, int(target * catchall_share + 0.5))
    catchall_n = 0
    while i < len(queue) and len(out) < target:
        if deadline and time.time() > deadline:
            dropped.append({"reason": "time limit reached"})
            break
        if tr.spend(service) - s0 - s_disc > contact_cap:
            dropped.append({"reason": f"contact budget ${contact_cap} used up"})
            break
        batch = queue[i:i + 6]          # six companies at a time (treg calls are slow, not expensive)
        i += 6
        results = discover.pmap(lambda c: contact.contact(c["domain"], owner_name=c.get("owner_name")), batch, workers=6)
        for c, r in zip(batch, results):
            if len(out) >= target:
                break
            if not r.get("verified"):
                dropped.append({"company": c["company"], "domain": c["domain"], "reason": r.get("reason")})
                continue
            if r.get("catchall"):
                if catchall_n >= catchall_max:
                    dropped.append({"company": c["company"], "domain": c["domain"], "reason": "catch-all cap reached"})
                    continue
                catchall_n += 1
            c["fields"] = {k: (re.sub(r"[\u2013\u2014]", "-", v) if isinstance(v, str) else v) for k, v in c["fields"].items()}  # dashes fail the lint
            lead = {"service": service, "template": c["template"], "company": c["company"], "domain": c["domain"], "city": c.get("city"),
                    "first_name": r["first"], "last_name": r["last"], "title": r["title"], "email": r["email"], "verdict": "accept_all" if r.get("catchall") else "valid",
                    "email_source": r["email_source"], "name_source": r["name_source"], "signal_plain": c["signal_plain"],
                    "evidence_urls": c.get("evidence_urls", []), "fields": c["fields"], "tier": c.get("tier", "A")}
            _, _, issues = render_emails.render(dict(template=c["template"], first_name=r["first"], company_name=c["company"], **c["fields"]))
            if issues:
                dropped.append({"company": c["company"], "domain": c["domain"], "reason": "lint: " + "; ".join(issues)})
                continue
            out.append(lead)
            if partial is not None:
                partial.append(lead)
    spent = tr.spend(service) - s0
    for l in out:
        l["spend_usd"] = round(spent / max(len(out), 1), 4)
    return {"leads": out, "dropped": dropped, "candidates": len(cands), "spend_usd": round(spent, 4),
            "discovery_usd": round(s_disc, 4), "seconds": round(time.time() - t0)}


def funnel_row(service, res, run_date):
    """One line per service per day for the weekly analysis: candidates -> verified leads, drop reasons, spend."""
    reasons = {}
    for d in res.get("dropped", []):
        k = (d.get("reason") or "unknown").split(":")[0][:40]
        reasons[k] = reasons.get(k, 0) + 1
    kept = len(res.get("leads", []))
    return {"date": run_date, "service": service, "tier": "C" if any(l.get("tier") == "C" for l in res.get("leads", [])) else "A", "candidates": res.get("candidates", 0), "verified_kept": kept, "catchall_kept": sum(1 for l in res.get("leads", []) if l.get("verdict") == "accept_all"),
            "dropped": len(res.get("dropped", [])), "drop_reasons": reasons, "spend_usd": res.get("spend_usd", 0),
            "usd_per_lead": round(res.get("spend_usd", 0) / kept, 4) if kept else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("service")
    ap.add_argument("--target", type=int, default=4)
    ap.add_argument("--out")
    ap.add_argument("--exclude")
    ap.add_argument("--contact-cap", type=float, default=0.60)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--tier-c", action="store_true", help="fit-only leads with a personal opener (service 11 template 11-intro)")
    ap.add_argument("--max-minutes", type=float, default=20, help="hard time limit; partial results are still written")
    a = ap.parse_args()
    ex = []
    if a.exclude:
        try:
            d = json.load(open(a.exclude))
            ex = d if isinstance(d, list) else list(d)
        except Exception:
            pass
    import threading
    partial, box = [], {}
    spend0 = tr.spend(a.service)
    t_end = time.time() + a.max_minutes * 60
    th = threading.Thread(target=lambda: box.update(res=run(a.service, a.target, ex, a.contact_cap, deadline=t_end - 120, partial=partial, tier_c=a.tier_c, shard=a.shard, shards=a.shards)), daemon=True)
    th.start()
    while th.is_alive() and time.time() < t_end:   # wall-clock watchdog (join(timeout) uses a clock that pauses while the laptop sleeps)
        th.join(5)
    if "res" in box:
        res = box["res"]
    else:  # hard time limit: keep whatever was found, never exit with no output
        res = {"leads": list(partial), "dropped": [{"reason": f"hard time limit {a.max_minutes} min"}], "spend_usd": round(tr.spend(a.service) - spend0, 4),
               "candidates": None}
    if a.out:
        json.dump(res["leads"], open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "leads"}, indent=1))
    print(f"service {a.service}: {len(res['leads'])} verified leads, ${res['spend_usd']} spent")
    for l in res["leads"]:
        print(" -", l["company"], "|", l["first_name"], l["last_name"], "|", l["email"], f"({l['email_source']})", "|", l["signal_plain"][:90])
    sys.stdout.flush()
    import os
    os._exit(0)  # do not wait for stuck worker threads
