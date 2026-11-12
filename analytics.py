"""Campaign analysis from Instantly (read-only, free API calls; no Graphed needed).
Usage: python3 analytics.py [--json out.json]   (INSTANTLY_API_KEY in env)
Per SCE campaign: sent, delivered, bounce / reply / positive-reply / unsubscribe rates, and the same sliced by the tags the
routine writes on each lead (svc, template, city, contactTitle, emailSource, runDate). Open rate is not measured (tracking is off).
"""
import argparse
import collections
import json
import os

import instantly

HERE = os.path.dirname(os.path.abspath(__file__))
TH = json.load(open(os.path.join(HERE, "analysis_thresholds.json")))
POSITIVE = {1, 2}  # Instantly lt_interest_status: 1 interested, 2 meeting booked


def sce_campaigns():
    return [c for c in instantly.list_campaigns() if c.get("name", "").startswith("SCE |")]


def campaign_stats():
    d = instantly.api("GET", "/campaigns/analytics")
    rows = d if isinstance(d, list) else d.get("items", [])
    return {r.get("campaign_id"): r for r in rows}


def all_leads(campaign_id, max_pages=50):
    out, cursor = [], None
    for _ in range(max_pages):
        body = {"campaign": campaign_id, "limit": 100}
        if cursor:
            body["starting_after"] = cursor
        d = instantly.api("POST", "/leads/list", body)
        out += d.get("items", [])
        cursor = d.get("next_starting_after")
        if not cursor:
            break
    return out


def rate(n, d):
    return round(n / d, 4) if d else None


def grade(m, key, delivered):
    if delivered < TH["min_delivered_for_verdict"]:
        return "too early"
    t, v = TH.get(key, {}), m.get(key)
    if v is None:
        return "no data"
    if "red_above" in t and v > t["red_above"]:
        return "red"
    if "red_below" in t and v < t["red_below"]:
        return "red"
    if "green_below" in t and v < t["green_below"]:
        return "green"
    if "green_above" in t and v > t["green_above"]:
        return "green"
    return "yellow"


def slice_leads(leads, tag):
    g = collections.defaultdict(lambda: {"leads": 0, "replied": 0, "positive": 0})
    for l in leads:
        k = (l.get("payload") or {}).get(tag) or "(untagged)"
        g[k]["leads"] += 1
        g[k]["replied"] += 1 if (l.get("email_reply_count") or 0) > 0 else 0
        g[k]["positive"] += 1 if l.get("lt_interest_status") in POSITIVE else 0
    return dict(g)


def report():
    stats, out = campaign_stats(), []
    for c in sce_campaigns():
        s = stats.get(c["id"], {})
        sent, bounced = s.get("emails_sent_count", 0) or 0, s.get("bounced_count", 0) or 0
        delivered = max(sent - bounced, 0)
        leads = all_leads(c["id"])
        replies = s.get("reply_count_unique", s.get("reply_count", 0)) or 0
        positive = sum(1 for l in leads if l.get("lt_interest_status") in POSITIVE)
        m = {"bounce_rate": rate(bounced, sent), "reply_rate": rate(replies, delivered),
             "positive_reply_rate": rate(positive, delivered), "unsubscribe_rate": rate(s.get("unsubscribed_count", 0) or 0, delivered)}
        out.append({"campaign": c["name"], "id": c["id"], "leads": len(leads), "sent": sent, "delivered": delivered, "bounced": bounced,
                    "replies": replies, "positive": positive, **m,
                    "grades": {k: grade(m, k, delivered) for k in m},
                    "by_tag": {t: slice_leads(leads, t) for t in ("svc", "city", "contactTitle", "emailSource", "runDate")}})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    r = report()
    if a.json:
        json.dump(r, open(a.json, "w"), indent=1)
    for x in r:
        print(f"{x['campaign'][:48]:48} leads {x['leads']:4} sent {x['sent']:4} bounce {x['bounce_rate']} reply {x['reply_rate']} pos {x['positive']} {set(x['grades'].values())}")
