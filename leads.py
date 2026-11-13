"""Signal search + contact finding helpers (treg). Fixes from the 2026-11-09 test run:
 - review dates: ISO or relative text ("7 months ago") are both handled
 - company lookup: name matches are checked against the returned website, wrong matches are dropped
 - contact: real person names only, real titles, verified ("valid") emails only
 - Indeed: tries "United States" then a bare state, never "City, ST"
"""
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

import tr

CHAINS = re.compile(
    r"roto-rooter|mr\.? rooter|one hour|aire serv|abc home|lowe'?s|home depot|service experts|turner|clayco|hensel|"
    r"granite|dpr |whiting|skanska|brookfield|woodside|lennar|pulte|d\.?r\.? horton|kb home|toll brothers|"
    r"meritage|taylor morrison|highland homes|perry homes|crst|amerihealth|caritas|kaiser|humana|aetna|cigna|anthem|centene|molina|"
    r"unitedhealth|blue cross|pepper construction|walsh (group|construction)|mortenson|hoffman construction|gilbane|mccarthy building|kiewit|jacobs engineering|clark construction", re.I)
SKIP_SITES = ("facebook.com", "instagram.com", "yelp.com", "linkedin.com", "google.com", "angi.com", "houzz.com")
CORP_WORDS = re.compile(r"\b(inc|llc|ltd|corp|company|co|group|construction|builders|homes|services|associates|holdings|dba)\b", re.I)
STOP = {"llc", "inc", "co", "company", "the", "and", "group", "corp", "ltd", "of", "services"}


def domain_of(url):
    if not url:
        return None
    h = urllib.parse.urlparse(url if "//" in url else "//" + url).netloc.lower()
    h = re.sub(r"^(www|m)\.", "", h)
    if not h or any(s in h for s in SKIP_SITES):
        return None
    return h


# ---------- dates ----------
def months_ago(date_str, now=None):
    """Age in months of an ISO date or relative text. None if unknown."""
    if not date_str:
        return None
    now = now or datetime.now(timezone.utc)
    s = str(date_str).strip().lower()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        d = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
        return (now - d).days / 30.4
    m = re.match(r"(a|an|\d+)\s+(day|week|month|year)s?\s+ago", s)
    if m:
        n = 1 if m.group(1) in ("a", "an") else int(m.group(1))
        return n * {"day": 1 / 30.4, "week": 7 / 30.4, "month": 1, "year": 12}[m.group(2)]
    return None


def within_months(date_str, months):
    a = months_ago(date_str)
    return a is not None and a <= months


# ---------- treg searches ----------
def maps(q):
    r = tr.call("treg.google.serp.maps", {"q": q}, max_cost=0.05)
    o = r.get("output") or {}
    return (o.get("places") if isinstance(o, dict) else o) or []


def reviews(place_id, limit=25):
    r = tr.call("treg.google.maps.reviews", {"place_id": place_id, "limit": limit, "sort": "newest"}, max_cost=0.02)
    return (r.get("output") or {}).get("reviews") or []


def jobs(query, locations=("United States", ""), limit=15):
    """Indeed search. City-and-state locations return nothing; try these in order until rows come back."""
    for loc in locations:
        r = tr.call("crawl4ai.indeed.search.jobs", {"query": query, "location": loc, "limit": limit}, max_cost=0.02)
        rows = r.get("rows") or []
        if rows:
            return rows
    return []


def enrich_domain(domain):
    r = tr.call("treg.companies.enrich", {"domain": domain}, max_cost=0.01)
    o = r.get("output") or {}
    return o if isinstance(o, dict) else {}


def enrich_name(name):
    r = tr.call("treg.companies.enrich", {"name": name}, max_cost=0.01)
    o = r.get("output") or {}
    return o if isinstance(o, dict) else {}


GENERIC = {"construction", "builders", "builder", "homes", "home", "residential", "design", "build", "remodel",
           "remodeling", "contracting", "contractors", "roofing", "plumbing", "heating", "cooling", "paving", "grading",
           "development", "developers", "properties", "realty", "advisors", "associates", "solutions", "custom"}


def tokens(name):
    return {t for t in re.findall(r"[a-z0-9]+", (name or "").lower()) if len(t) > 2 and t not in STOP}


def name_matches(company, domain, returned_name=""):
    """True if most of the company's distinctive words appear in the returned website/name.
    Guards against wrong lookups, e.g. 'Frank Gay Residential' -> franklloydwright.org (only 'frank' overlaps)."""
    toks = tokens(company)
    distinct = {t for t in toks if t not in GENERIC} or toks
    if not distinct:
        return False
    hay = re.sub(r"[^a-z0-9]", "", (domain or "").lower()) + " " + re.sub(r"[^a-z0-9 ]", "", (returned_name or "").lower())
    hits = sum(1 for t in distinct if t in hay)
    return hits / len(distinct) >= 0.6


def headcount(o):
    for k in ("employee_count", "employees", "headcount", "employee_count_range", "size"):
        v = o.get(k)
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str):
            nums = [int(x) for x in re.findall(r"\d+", v.replace(",", ""))]
            if nums:
                return nums[0]
    return None


# ---------- signals ----------
def review_signal(query, pattern, max_places=12, per=25, months=12, exclude=()):
    """First non-chain business with a 1-3 star review in the last `months` matching `pattern`."""
    rx = re.compile(pattern, re.I)
    seen = 0
    for p in maps(query):
        dom = domain_of(p.get("website"))
        if CHAINS.search(p.get("name", "")) or not dom or dom in exclude:
            continue
        seen += 1
        if seen > max_places:
            break
        for rv in reviews(p["place_id"], per):
            txt = (rv.get("text") or "").strip()
            if (rv.get("rating") or 5) <= 3 and rx.search(txt) and within_months(rv.get("date"), months):
                return {"company": p["name"], "domain": dom, "place_id": p["place_id"], "reviewSource": "Google",
                        "reviewTextFull": txt[:400], "reviewDate": rv.get("date"), "rating": rv.get("rating"),
                        "placesChecked": seen}
    return None


def job_signal(query, need=None, exclude=(), days=45, min_hc=5, max_hc=250, locations=("United States", "")):
    """First company posting this job in the last `days`, resolved to a verified website and a fitting headcount."""
    for r in jobs(query, locations=locations):
        name = r.get("company") or ""
        if CHAINS.search(name):
            continue
        pub = r.get("published")
        if pub and months_ago(pub) is not None and months_ago(pub) * 30.4 > days:
            continue
        if need and not re.search(need, (r.get("snippet") or "") + " " + (r.get("title") or ""), re.I):
            continue
        o = enrich_name(name)
        dom = domain_of(o.get("website") or o.get("domain"))
        if not dom or dom in exclude:
            continue
        if not name_matches(name, dom, o.get("name") or ""):
            continue  # wrong company (e.g. "Gregory Construction" -> a Thai firm)
        hc = headcount(enrich_domain(dom)) if headcount(o) is None else headcount(o)
        if hc is not None and not (min_hc <= hc <= max_hc):
            continue
        return {"company": name, "domain": dom, "role": r.get("title"), "published": pub, "url": r.get("url"),
                "headcount": hc, "snippet": r.get("snippet")}
    return None


# ---------- contacts ----------
PRIORITY = [("owner", 0), ("founder", 1), ("ceo", 2), ("chief executive", 2), ("president", 3),
            ("managing", 4), ("principal", 5), ("general manager", 6)]


def looks_like_person(name):
    parts = (name or "").replace(".", " ").split()
    return 2 <= len(parts) <= 4 and all(re.fullmatch(r"[A-Za-z'\-]+", p) for p in parts) and not CORP_WORDS.search(name)


BAD_TITLE = re.compile(r"agency|franchise|division|regional|branch|district|dealer|territory|insurance|assistant|sales (rep|consultant|associate)|"
                       r"manager of|vice|\bvp\b|publisher|editor|journalist|advertis|columnist", re.I)


def pick_exec(people):
    best = None
    for p in people:
        t = (p.get("title") or p.get("headline") or "").lower()
        name = p.get("full_name") or p.get("name") or ""
        if not looks_like_person(name) or BAD_TITLE.search(t):
            continue
        for key, rank in PRIORITY:
            if key in t:
                if best is None or rank < best[0]:
                    best = (rank, p)
                break
    return best[1] if best else None


def contact(domain, owner_name=None, owner_title=None):
    """Find the decision-maker and a verified email. Returns a dict with verified=True only on a 'valid' verdict."""
    if owner_name:
        if not looks_like_person(owner_name):
            return {"reason": f"owner_name not a person: {owner_name}"}
        full, title = owner_name, owner_title or "(from company website)"
    else:
        people = []
        for q in ("owner", "owner, founder, CEO or president"):
            r = tr.call("treg.people.search", {"company_domain": domain, "q": q, "limit": 10}, max_cost=0.02)
            o = r.get("output") or {}
            people = (o.get("people") if isinstance(o, dict) else o) or []
            if people:
                p = pick_exec(people)
                if p:
                    break
        else:
            p = None
        if not p:
            return {"reason": "no owner/CEO/president found"}
        full = p.get("full_name") or p.get("name")
        title = p.get("title") or p.get("headline")
    parts = full.split()
    r = tr.call("treg.people.email.find", {"domain": domain, "first_name": parts[0], "last_name": parts[-1]},
                max_cost=0.05, headers=["X-Treg-Route-Verify: true"])
    o = r.get("output") or {}
    email = o.get("email") if isinstance(o, dict) else None
    ver = (r.get("_treg") or {}).get("verification") or {}
    verdict = str(ver.get("verdict") or "").lower()
    if not email:
        return {"name": full, "title": title, "reason": "no email found"}
    return {"name": full, "first": parts[0], "last": parts[-1], "title": title, "email": email,
            "verdict": verdict, "verified": verdict == "valid", "domain_match": (r.get("_treg") or {}).get("domain_match")}


# ---------- permits (free open data, no treg) ----------
def socrata_top_contractors(resource_url, field, date_field, since_iso, limit=15):
    """Count permits per contractor from a Socrata dataset, e.g. Austin: data.austintexas.gov/resource/3syk-w9eu."""
    import json
    import urllib.request
    q = urllib.parse.urlencode({
        "$select": f"{field},count(*) as n", "$where": f"{date_field} > '{since_iso}'",
        "$group": field, "$order": "n desc", "$limit": str(limit)})
    with urllib.request.urlopen(f"https://{resource_url}.json?{q}", timeout=40) as r:
        return json.load(r)
