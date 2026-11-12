"""Add reviewed leads to their template's Instantly campaign and activate those campaigns. The ONLY script the routine runs to send.
Usage: python3 add_leads_to_instantly.py --leads /tmp/out/final_leads.json --run-date 2026-11-12 [--cap 45]
Input: JSON list of finder leads that already passed the merge, "valid" verdict and render checks.
Guards: approved templates only (others are skipped and reported), daily cap, one add call per campaign, never retried.
Prints a JSON summary. Needs INSTANTLY_API_KEY."""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import instantly
import services

ap = argparse.ArgumentParser()
ap.add_argument("--leads", required=True)
ap.add_argument("--run-date", default=datetime.date.today().isoformat())
ap.add_argument("--cap", type=int, default=45)
a = ap.parse_args()

leads = json.load(open(a.leads))
camps = {v["template"]: k for k, v in json.load(open(os.path.join(HERE, "campaigns.json"))).items()}
approved = set(services.approved_templates())
sent_today = instantly.sent_since(a.run_date + "T00:00:00Z")
room = max(0, a.cap - sent_today)
by_camp, skipped = {}, []
for l in leads:
    t = l["template"]
    if t not in approved or t not in camps or "@" not in (l.get("email") or "") or l.get("verdict") != "valid":
        skipped.append({"company": l.get("company"), "template": t, "reason": "template not approved/no campaign, or not a valid email"})
    elif sum(len(v) for v in by_camp.values()) >= room:
        skipped.append({"company": l.get("company"), "template": t, "reason": "daily cap"})
    else:
        by_camp.setdefault(camps[t], []).append(l)
result = {"added": {}, "activated": [], "errors": [], "skipped": skipped, "sent_today": sent_today}
for cid, ls in by_camp.items():
    try:
        r = instantly.add_leads(cid, [instantly.lead_payload(l, a.run_date) for l in ls])
        result["added"][cid] = {"n": len(ls), "response": str(r)[:200]}
        instantly.activate(cid)
        result["activated"].append(cid)
    except Exception as e:  # never retry a send
        result["errors"].append({"campaign": cid, "error": repr(e)[:200]})
print(json.dumps(result, indent=1))
