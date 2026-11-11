"""Keep the email text inside Instantly campaigns identical to the templates in services.py.
  python sync_campaigns.py --check    report drift (exit 1 if any)
  python sync_campaigns.py --apply    rewrite drifted campaigns from services.py
Uses campaigns.json (campaign id -> template). Needs INSTANTLY_API_KEY.
"""
import json
import os
import re
import sys

import instantly
import services

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()


def current(cid):
    d = instantly.api("GET", f"/campaigns/{cid}")
    try:
        v = d["sequences"][0]["steps"][0]["variants"][0]
        return v.get("subject", ""), v.get("body", "")
    except Exception:
        return None, None


def main(apply=False):
    camps = json.load(open(os.path.join(HERE, "campaigns.json")))
    drift = []
    for cid, c in camps.items():
        subject, body = services.build(c["template"])
        cs, cb = current(cid)
        if cs is None:
            drift.append((c["template"], cid, "could not read campaign"))
            continue
        if norm(cs) != norm(subject) or norm(cb) != norm(body):
            drift.append((c["template"], cid, "email text differs from services.py"))
            if apply:
                r = instantly.api("PATCH", f"/campaigns/{cid}", {"sequences": [{"steps": [{"type": "email", "delay": 0,
                                  "variants": [{"subject": subject, "body": body}]}]}]})
                print("  updated", c["template"], "->", "ok" if "_error" not in r else r["_error"][:100])
    for t, cid, why in drift:
        print(f"DRIFT {t} ({cid[:8]}): {why}")
    print(f"{len(camps)} campaigns checked, {len(drift)} drifted")
    return len(drift)


if __name__ == "__main__":
    n = main(apply="--apply" in sys.argv)
    sys.exit(1 if (n and "--apply" not in sys.argv) else 0)
