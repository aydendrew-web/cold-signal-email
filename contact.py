"""Contact step v2: owner name -> verified email, with fallbacks.

Order (cheap and free first):
 1. Owner name from the company's own website (free): About / Team / Contact pages.
 2. If none, treg people search (q="owner"), real person names only.
 3. treg email find with verification.
 4. If that finds nothing: try common address formats (first@, first.last@, ...) and verify each
    with treg.people.email.verify (about $0.002 a check). Only "safe" addresses count.
 5. Accept an email on a different domain only if it is clearly the same company
    (related names, or the domain appears on the company's own site).
"""
import re
import urllib.request
from difflib import SequenceMatcher

import tr
import leads

UA = {"User-Agent": "Mozilla/5.0 (compatible; research)"}
PAGES = ["", "about", "about-us", "our-team", "team", "meet-the-team", "our-story", "contact", "contact-us", "leadership"]
TITLE = (r"(?:owner|co-?owner|founder|co-?founder|president|ceo|chief executive officer|principal|"
         r"managing (?:partner|member|director)|general manager)")
NAME = r"([A-Z][a-z]{1,15}(?:\s[A-Z]\.?)?\s[A-Z][A-Za-z'\-]{1,20})"
NOT_NAMES = {"our", "meet", "the", "contact", "about", "call", "request", "free", "get", "view", "learn", "read", "home",
             "welcome", "licensed", "customer", "service", "services", "team", "leadership", "company", "general",
             "project", "managing", "chief", "vice", "senior", "executive", "family", "local", "quality", "your", "manager", "president",
             "owner", "founder", "director", "sales", "operations", "office", "branch", "regional", "division", "assistant",
             "coordinator", "estimator", "superintendent", "principal", "partner", "member", "co", "ceo"}
GENERIC = {"info", "ask", "contact", "support", "sales", "admin", "hello", "office", "mail", "service", "services", "team", "help",
           "inquiries", "customerservice", "estimates", "billing", "accounting", "careers", "jobs", "hr", "marketing", "noreply"}
RANK = [("owner", 0), ("founder", 1), ("ceo", 2), ("chief executive", 2), ("president", 3), ("principal", 4),
        ("managing", 5), ("general manager", 6)]
_cache = {}


def fetch(url, timeout=14):
    if url in _cache:
        return _cache[url]
    try:
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=timeout).read(600000).decode("utf-8", "ignore")
    except Exception:
        html = ""
    _cache[url] = html
    return html


def page_text(html):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = t.replace("&amp;", "&").replace("&#8217;", "'").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", t)


def _title_rank(t):
    t = t.lower()
    for k, r in RANK:
        if k in t:
            return r
    return 9


def owner_from_site(domain, max_pages=6):
    """Return [(name, title)] found on the company's own pages, best title first."""
    found = {}
    fetched = 0
    for p in PAGES:
        if fetched >= max_pages:
            break
        html = fetch(f"https://{domain}/{p}".rstrip("/") if p else f"https://{domain}/")
        if not html:
            html = fetch(f"https://www.{domain}/{p}".rstrip("/") if p else f"https://www.{domain}/")
        if not html:
            continue
        fetched += 1
        text = page_text(html)
        for m in re.finditer(NAME + r"\s*[,\-–—|:(]\s*(" + TITLE + r")\b", text):
            found.setdefault(m.group(1).strip(), m.group(2))
        for m in re.finditer(r"\b(" + TITLE + r")\s*[:\-–—,|]?\s*" + NAME, text):
            found.setdefault(m.group(2).strip(), m.group(1))
        # "Name is the owner/founder/president"
        for m in re.finditer(NAME + r"\s+(?:is|serves as|has been)\s+(?:the\s+|our\s+)?(" + TITLE + r")\b", text):
            found.setdefault(m.group(1).strip(), m.group(2))
        if found:
            break
    out = []
    for name, title in found.items():
        first = name.split()[0].lower()
        if first in NOT_NAMES or name.split()[-1].lower() in NOT_NAMES or not leads.looks_like_person(name) or leads.BAD_TITLE.search(title):
            continue
        out.append((name, title))
    out.sort(key=lambda x: _title_rank(x[1]))
    return out


def people_search(domain):
    for q in ("owner", "owner, founder, CEO or president"):
        r = tr.call("treg.people.search", {"company_domain": domain, "q": q, "limit": 10}, max_cost=0.02)
        o = r.get("output") or {}
        people = (o.get("people") if isinstance(o, dict) else o) or []
        p = leads.pick_exec(people)
        if p:
            return (p.get("full_name") or p.get("name")), (p.get("title") or p.get("headline") or "")
    return None


def patterns(first, last, domain):
    f, l = first.lower(), last.lower()
    f, l = re.sub(r"[^a-z]", "", f), re.sub(r"[^a-z]", "", l)
    return [f"{f}@{domain}", f"{f}.{l}@{domain}", f"{f}{l}@{domain}", f"{f[0]}{l}@{domain}",
            f"{l}@{domain}", f"{f}{l[0]}@{domain}", f"{f[0]}.{l}@{domain}", f"{f}_{l}@{domain}", f"{l}{f[0]}@{domain}"]


def site_emails(domain, first, last):
    """Personal-looking addresses printed on the company's own pages that contain the owner's first or last name."""
    f, l = re.sub(r"[^a-z]", "", first.lower()), re.sub(r"[^a-z]", "", last.lower())
    found = []
    for p in ("", "contact", "contact-us", "about", "about-us"):
        html = fetch(f"https://{domain}/{p}" if p else f"https://{domain}/")
        for m in re.finditer(r"[A-Za-z0-9._%+-]+@" + re.escape(domain), html or "", re.I):
            e = m.group(0).lower()
            local = e.split("@")[0]
            if local not in GENERIC and (f in local or (len(l) > 2 and l in local)) and e not in found:
                found.append(e)
    return found


def verify_status(email):
    r = tr.call("treg.people.email.verify", {"email": email}, max_cost=0.02)
    o = r.get("output") or {}
    return str(o.get("status", "")).lower() if isinstance(o, dict) else ""


def verify(email):
    """True only if treg says the mailbox is valid and safe (catch-all/unknown do not count)."""
    r = tr.call("treg.people.email.verify", {"email": email}, max_cost=0.02)
    o = r.get("output") or {}
    return bool(isinstance(o, dict) and o.get("valid") is True and str(o.get("status", "")).lower() in ("safe", "valid", "deliverable", "ok"))


def _norm(d):
    d = d.lower().split(":")[0]
    d = re.sub(r"^www\.", "", d)
    return re.sub(r"[^a-z0-9]", "", d.rsplit(".", 1)[0]) if "." in d else d


def domains_related(site_domain, email_domain):
    """Same company on a different domain (stancraft.com vs stancraftcg.com), or the site itself shows the email domain."""
    if site_domain == email_domain:
        return True
    a, b = _norm(site_domain), _norm(email_domain)
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= 5 and long_.startswith(short):
        return True
    if SequenceMatcher(None, a, b).ratio() >= 0.8:
        return True
    for p in ("", "contact", "contact-us", "about"):
        html = fetch(f"https://{site_domain}/{p}" if p else f"https://{site_domain}/")
        if html and re.search(r"@" + re.escape(email_domain), html, re.I):
            return True
    return False


def _find(domain, first, last):
    r = tr.call("treg.people.email.find", {"domain": domain, "first_name": first, "last_name": last},
                max_cost=0.03, headers=["X-Treg-Route-Verify: true"])
    o = r.get("output") or {}
    email = o.get("email") if isinstance(o, dict) else None
    ver = (r.get("_treg") or {}).get("verification") or {}
    ok = str(ver.get("verdict") or "").lower() == "valid"
    return email, ok


def contact(domain, owner_name=None, owner_title=None, max_names=3):
    """Find a decision-maker and a verified email. Returns {verified: True, ...} or {reason: ...}."""
    names = []
    source = None
    if owner_name and leads.looks_like_person(owner_name):
        names.append((owner_name, owner_title or "(provided)"))
        source = "given"
    if not names:
        names = owner_from_site(domain)
        source = "website" if names else None
    if not names:
        ps = people_search(domain)
        if ps and leads.looks_like_person(ps[0]):
            names = [ps]
            source = "people-search"
    if not names:
        return {"reason": "no owner name found (site and people search)"}
    last_reason = "no email found"
    names = [(n, ti) for n, ti in names if not leads.BAD_TITLE.search(ti or "")] or names
    for full, title in names[:max_names]:
        parts = full.replace(".", " ").split()
        first, last = parts[0], parts[-1]
        email, ok = _find(domain, first, last)
        if email and ok and email.split("@")[0].lower() in GENERIC:
            last_reason = "email is a generic mailbox"
            email = None
        if email and ok:
            ed = email.split("@")[-1].lower()
            if domains_related(domain, ed):
                return {"verified": True, "name": full, "first": first, "last": last, "title": title, "email": email,
                        "email_source": "find", "name_source": source}
            last_reason = f"email on unrelated domain {ed}"
        guesses = list(dict.fromkeys(site_emails(domain, first, last) + patterns(first, last, domain)))
        if verify_status(guesses[0]) == "accept_all":   # catch-all domain: every address "verifies", so no guess can be proven. Stop spending.
            return {"verified": False, "name": full, "title": title, "reason": "catch-all domain (cannot verify)", "catchall": guesses[0]}
        from concurrent.futures import ThreadPoolExecutor   # verify all guesses at once, keep the first valid one in pattern order
        with ThreadPoolExecutor(max_workers=5) as ex:
            verdicts = list(ex.map(verify, guesses))
        for guess, ok_guess in zip(guesses, verdicts):
            if ok_guess:
                return {"verified": True, "name": full, "first": first, "last": last, "title": title, "email": guess,
                        "email_source": "pattern", "name_source": source}
        last_reason = last_reason if "unrelated" in last_reason else "no valid email (find + site + 9 patterns)"
    return {"verified": False, "name": names[0][0], "title": names[0][1], "reason": last_reason}
