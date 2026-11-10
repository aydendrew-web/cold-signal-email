"""Render a template for each lead and lint it. Usage:
    python render_emails.py leads.json            # each lead: {"template": "16-reporting", "first_name": ..., "company_name": ..., <fields>}
Prints each email and its issues; exits 1 if any lead has a problem. Also importable: render(lead) -> (subject, body, issues).
"""
import json
import re
import sys

import services

BANNED = re.compile(r"\b(automat\w*|platform\w*|leverag\w*)\b", re.I)


def render(lead):
    subject, body = services.build(lead["template"])
    vals = dict(lead)
    vals.setdefault("firstName", lead.get("first_name", ""))
    vals.setdefault("companyName", lead.get("company_name", ""))
    out = []
    for text in (subject, body):
        out.append(re.sub(r"\{\{(\w+)\}\}", lambda m: str(vals.get(m.group(1), m.group(0))), text))
    subject, body = out
    body += services.SIGNATURE
    issues = []
    text = subject + "\n" + body
    if BANNED.search(text):
        issues.append("banned word: " + BANNED.search(text).group(0))
    if "—" in text or "–" in text:
        issues.append("dash character")
    if "!" in text:
        issues.append("exclamation point")
    if re.search(r"\$\s?\d", text):
        issues.append("price")
    if re.search(r"\{\{\w+\}\}", text):
        issues.append("unfilled field: " + re.search(r"\{\{\w+\}\}", text).group(0))
    words = len(body.split("Ayden Hector")[0].split())
    if not 40 <= words <= 120:
        issues.append(f"length {words} words")
    q = vals.get("reviewQuote")
    if q and len(q.split()) > 15:
        issues.append("review quote over 15 words")
    if len(subject) > 70:
        issues.append("subject over 70 characters")
    missing = [f for f in services.TEMPLATES[lead["template"]]["fields"] if not str(vals.get(f, "")).strip()]
    if missing:
        issues.append("missing fields: " + ", ".join(missing))
    return subject, body, issues


if __name__ == "__main__":
    leads = json.load(open(sys.argv[1]))
    bad = 0
    for l in leads:
        s, b, issues = render(l)
        print(f"--- {l.get('template')} | {l.get('first_name')} @ {l.get('company_name')} | issues: {issues or 'none'}\nSubject: {s}\n\n{b}\n")
        bad += bool(issues)
    sys.exit(1 if bad else 0)
