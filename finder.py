"""Run one service end to end: discover candidates (stage 1), then find verified contacts (stage 2) within a budget.
Usage: python finder.py <service> [--target 4] [--out file.json] [--exclude file.json] [--contact-cap 0.6]
Writes {"leads": [...], "dropped": [...], "spend_usd": x}. A lead only appears if its email verified and its email passes the lint.
"""
import argparse
import json
import sys
import time

import contact
import discover
import render_emails
import tr


def run(service, target=4, exclude=(), contact_cap=0.60, discover_limit=15):
    tr.CURRENT["service"] = service
    t0 = time.time()
    s0 = tr.spend(service)
    try:
        cands = discover.discover(service, exclude=exclude, limit=discover_limit)
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
    while i < len(queue) and len(out) < target:
        if tr.spend(service) - s0 - s_disc > contact_cap:
            dropped.append({"reason": f"contact budget ${contact_cap} used up"})
            break
        batch = queue[i:i + 3]          # three companies at a time (treg calls are slow, not expensive)
        i += 3
        results = discover.pmap(lambda c: contact.contact(c["domain"], owner_name=c.get("owner_name")), batch, workers=3)
        for c, r in zip(batch, results):
            if len(out) >= target:
                break
            if not r.get("verified"):
                dropped.append({"company": c["company"], "domain": c["domain"], "reason": r.get("reason")})
                continue
            lead = {"service": service, "template": c["template"], "company": c["company"], "domain": c["domain"], "city": c.get("city"),
                    "first_name": r["first"], "last_name": r["last"], "title": r["title"], "email": r["email"], "verdict": "valid",
                    "email_source": r["email_source"], "name_source": r["name_source"], "signal_plain": c["signal_plain"],
                    "evidence_urls": c.get("evidence_urls", []), "fields": c["fields"]}
            _, _, issues = render_emails.render(dict(template=c["template"], first_name=r["first"], company_name=c["company"], **c["fields"]))
            if issues:
                dropped.append({"company": c["company"], "domain": c["domain"], "reason": "lint: " + "; ".join(issues)})
                continue
            out.append(lead)
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
    return {"date": run_date, "service": service, "candidates": res.get("candidates", 0), "verified_kept": kept,
            "dropped": len(res.get("dropped", [])), "drop_reasons": reasons, "spend_usd": res.get("spend_usd", 0),
            "usd_per_lead": round(res.get("spend_usd", 0) / kept, 4) if kept else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("service")
    ap.add_argument("--target", type=int, default=4)
    ap.add_argument("--out")
    ap.add_argument("--exclude")
    ap.add_argument("--contact-cap", type=float, default=0.60)
    a = ap.parse_args()
    ex = []
    if a.exclude:
        try:
            d = json.load(open(a.exclude))
            ex = d if isinstance(d, list) else list(d)
        except Exception:
            pass
    res = run(a.service, a.target, ex, a.contact_cap)
    if a.out:
        json.dump(res["leads"], open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "leads"}, indent=1))
    print(f"service {a.service}: {len(res['leads'])} verified leads, ${res['spend_usd']} spent")
    for l in res["leads"]:
        print(" -", l["company"], "|", l["first_name"], l["last_name"], "|", l["email"], f"({l['email_source']})", "|", l["signal_plain"][:90])
