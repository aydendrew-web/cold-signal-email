"""Stage 1: find candidate companies with a real signal, per service. Cheap calls only; no contact lookups here.
Each discoverer returns a list of candidate dicts:
  {service, template, company, domain, city, signal_plain, evidence_urls, score, fields:{...}, owner_name?}
Candidates are ranked best first. contact.py (stage 2) turns them into verified leads.
"""
import datetime
import json
import re
import urllib.parse
import urllib.request

import contact
import leads
import tr

CITIES = ["Austin TX", "Dallas TX", "Houston TX", "San Antonio TX", "Phoenix AZ", "Denver CO", "Atlanta GA", "Nashville TN",
          "Charlotte NC", "Raleigh NC", "Tampa FL", "Orlando FL", "Salt Lake City UT", "Boise ID", "Indianapolis IN",
          "Columbus OH", "Kansas City MO", "Minneapolis MN", "Jacksonville FL", "Las Vegas NV"]
BIG = re.compile(r"milestone|century|brookfield|perry homes|taylor morrison|kb home|horton|weekley|pulte|lennar|meritage|"
                 r"newhomeco|new home co|highland|toll bro|ashton|beazer|shea homes|mi homes|ryan homes|nvr|fischer homes|"
                 r"tri ?pointe|drees|lgi homes|stanley martin|landsea|dream finders|clayton homes|chesmar|empire communities|"
                 r"davidson homes|smith douglas|century communities|forestar|hovnanian|m/i homes|william lyon|woodside", re.I)


def pmap(fn, items, workers=4):
    """Run fn over items in a few threads (treg calls are slow but cheap)."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def cities(n, offset=0):
    """Rotate through cities by day so each day looks in new places."""
    start = (datetime.date.today().toordinal() + offset) % len(CITIES)
    return [CITIES[(start + i) % len(CITIES)] for i in range(n)]


def article(role):
    return "an" if role.strip()[:1].lower() in "aeiou" else "a"


def clean_role(t):
    t = re.sub(r"\s*\(.*?\)|\s*-\s*remote.*|\s*,.*$", "", t or "").replace("&", "and").strip()
    return t[:60]


def quote_from(text, rx, max_words=14):
    """Short verbatim excerpt that contains the match and ends cleanly (no quote marks, no cut-off words)."""
    m = rx.search(text)
    if not m:
        return None
    text = re.sub(r"[\"\u201c\u201d]", "", text)
    m = rx.search(text)
    sentence = text
    pos = 0
    for part in re.split(r"(?<=[.!?])\s+|\n+", text):
        i = text.find(part, pos)
        if i <= m.start() < i + len(part):
            sentence = part
            break
        pos = i + len(part)
    words = sentence.split()
    if len(words) <= max_words:
        return " ".join(words).strip(" .,'-")
    for clause in re.split(r"[,;:\u2013\u2014]\s+|\s-\s", sentence):
        if rx.search(clause) and 3 <= len(clause.split()) <= max_words:
            return clause.strip(" .,'-")
    pre = len(sentence[:rx.search(sentence).start()].split())
    start = max(0, pre - 3)
    return " ".join(words[start:start + max_words]).strip(" .,'-")


# ---------------------------------------------------------------------------- review-based
def review_candidates(service, template, queries, regex, theme=None, months=12, per=30, max_places=60, exclude=(), limit=15, source="Google"):
    rx = re.compile(regex, re.I)
    places, seen_dom = [], set()
    for rows, q in zip(pmap(leads.maps, queries), queries):
        for p in rows:
            dom = leads.domain_of(p.get("website"))
            if not dom or dom in exclude or dom in seen_dom or leads.CHAINS.search(p.get("name", "")) or BIG.search(p.get("name", "")):
                continue
            seen_dom.add(dom)
            places.append((p, dom, q))
    places = places[:max_places]

    def check(item):
        p, dom, q = item
        for rv in leads.reviews(p["place_id"], per):
            txt = (rv.get("text") or "").strip()
            if (rv.get("rating") or 5) <= 3 and rx.search(txt) and leads.within_months(rv.get("date"), months):
                quote = quote_from(txt, rx)
                if not quote:
                    continue
                f = {"reviewSource": source, "reviewQuote": quote}
                if theme:
                    f["reviewTheme"] = theme
                return dict(service=service, template=template, company=p["name"], domain=dom, city=q.split(" in ")[-1],
                            signal_plain=f"{rv.get('rating')}-star Google review ({rv.get('date')}): \"{quote}\"",
                            evidence_urls=[], score=10 - (leads.months_ago(rv.get("date")) or 6) / 2, fields=f)
        return None

    found = [c for c in pmap(check, places, workers=4) if c]
    return sorted(found, key=lambda c: -c["score"])[:limit]


def site_claims_24_7(domain):
    html = contact.fetch(f"https://{domain}/")
    m = re.search(r"(24\s?/\s?7[^.<]{0,40}|24[- ]hour[^.<]{0,30}|emergency (?:service|plumbing|hvac|repair)[^.<]{0,30})", contact.page_text(html), re.I)
    return m.group(1).strip()[:60] if m else None


# ---------------------------------------------------------------------------- Indeed-based
BAD_INDUSTRY = re.compile(r"staffing|recruit|software|information technology|it services|internet|government|education|defense|"
                          r"human resources|analytics|consulting|marketing|advertising|computer|telecom|e-?learning|university|school", re.I)


def jobs_candidates(service, template, queries, need=None, days=45, exclude=(), limit=15, min_hc=5, max_hc=250,
                    locations=("United States", ""), industry_ok=None, blocked=BAD_INDUSTRY, need_company=None, need_title=None):
    out, seen = [], set()
    for qy in queries:
        for r in leads.jobs(qy, locations=locations, limit=20):
            comp = (r.get("company") or "").strip()
            if not comp or comp.lower() in seen or leads.CHAINS.search(comp):
                continue
            seen.add(comp.lower())
            age = leads.months_ago(r.get("published"))
            if age is None or age * 30.4 > days:
                continue
            if need_title and not re.search(need_title, r.get("title") or "", re.I):
                continue
            blob = (r.get("snippet") or "") + " " + (r.get("title") or "")
            if need and not re.search(need, blob, re.I):
                continue
            # website from Google Maps (not name lookup), then check the name fits the site
            dom, city = None, (r.get("location") or "")
            for pl in leads.maps(f"{comp} {city}".strip())[:4]:
                d = leads.domain_of(pl.get("website"))
                if d and leads.name_matches(comp, d, pl.get("name", "")):
                    dom = d
                    break
            if not dom or dom in exclude:
                continue
            e = leads.enrich_domain(dom)
            hc = leads.headcount(e)
            ind = e.get("industry") or ""
            if hc is not None and not (min_hc <= hc <= max_hc):
                continue
            if blocked and blocked.search(ind):
                continue
            if industry_ok and not re.search(industry_ok, ind, re.I):
                continue
            if need_company and not re.search(need_company, (e.get("description") or "") + " " + ind + " " + comp, re.I):
                continue
            role = clean_role(r.get("title"))
            out.append(dict(service=service, template=template, company=comp, domain=dom, city=city, industry=ind, headcount=hc,
                            signal_plain=f"Indeed post {str(r.get('published'))[:10]} for {role} (~{hc} employees, {ind})",
                            evidence_urls=[r.get("url")] if r.get("url") else [], score=10 - age * 30.4 / 10,
                            fields={"role": role, "a_an": article(role)}))
            if len(out) >= limit:
                return out
    return out


KPI = [
    (r"hospital|health|medical|clinic", "patient visits vs. plan, new patient referrals, collections vs. billed, days in accounts receivable, and quality measure performance"),
    (r"bank|credit union|financial services|mortgage", "loans originated vs. plan, deposit growth, net interest margin, delinquencies, and member growth"),
    (r"construction|building|civil|engineering", "revenue vs. plan, backlog, job margins, receivables, and cash"),
    (r"manufactur|machinery|industrial|food production", "units shipped vs. plan, on-time delivery, scrap rate, gross margin, and cash"),
    (r"transport|trucking|logistics|freight", "loads hauled, revenue per mile, empty miles, driver turnover, and cash"),
    (r"non-?profit|charit|civic|social", "donations vs. plan, program spend, new donors, donor retention, and cash"),
    (r"retail|wholesale|consumer goods|distribution", "sales vs. plan, gross margin, inventory turns, new customers, and cash"),
    (r"real estate|property", "occupancy, rent collected vs. billed, delinquencies, maintenance backlog, and cash"),
]


def kpi_line(industry):
    for rx, line in KPI:
        if re.search(rx, industry or "", re.I):
            return line
    return None


# ---------------------------------------------------------------------------- permits (free open data)
def socrata(u, params):
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(f"https://{u}.json?{q}", headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as r:
        return json.load(r)


TRADE_NOT_BUILDER = re.compile(r"plumb|electric|hvac|air cond|mechanical|foundation|leak|irrigation|fire protection|elevator|heating|cooling", re.I)
NOT_HOMEBUILDER = re.compile(r"pool|spa\b|landscap|fence|roof|solar|paving|concrete|cabinet|window|garage|deck|patio|sign", re.I)


def austin_permit_counts(since_days=270, new_only=True, lo=5, hi=60, limit=60):
    since = (datetime.date.today() - datetime.timedelta(days=since_days)).isoformat()
    where = f"issue_date > '{since}' AND contractor_company_name is not null"
    where += " AND permit_type_desc='Building Permit' AND permit_class_mapped='Residential'"
    if new_only:
        where += " AND work_class='New'"
    rows = socrata("data.austintexas.gov/resource/3syk-w9eu", {
        "$select": "contractor_company_name,count(*) as n,min(issue_date) as first", "$where": where,
        "$group": "contractor_company_name", "$having": f"count(*) >= {lo} AND count(*) <= {hi}", "$order": "n desc", "$limit": str(limit)})
    return [(r["contractor_company_name"], int(r["n"]), r["first"][:10]) for r in rows]


def permit_candidates(service, template, new_only, exclude=(), limit=12, need_team=False, lo=5, hi=60):
    out = []
    for name, n, first in austin_permit_counts(new_only=new_only, lo=lo, hi=hi):
        clean = re.sub(r"\(.*?\)|\*+|,? ?(LLC|INC|LP|LTD)\.?$", "", name, flags=re.I).strip(" ,.")
        if BIG.search(clean) or leads.CHAINS.search(clean) or TRADE_NOT_BUILDER.search(clean) or (new_only and NOT_HOMEBUILDER.search(clean)):
            continue
        dom = None
        for pl in leads.maps(f"{clean} Austin TX")[:4]:
            d = leads.domain_of(pl.get("website"))
            if d and leads.name_matches(clean, d, pl.get("name", "")):
                dom = d
                break
        if not dom or dom in exclude:
            continue
        e = leads.enrich_domain(dom)
        hc = leads.headcount(e)
        blob = (e.get("industry") or "") + " " + (e.get("description") or "") + " " + clean
        if new_only and not re.search(r"home|build|residential|custom|develop|construct", blob, re.I):
            continue
        if need_team and not (hc and 3 <= hc <= 60):
            continue
        month = datetime.date.fromisoformat(first).strftime("%B")
        f = {"permitCount": str(n), "permitSince": month, "city": "Austin"}
        if need_team:
            f["teamSize"] = str(hc)
        out.append(dict(service=service, template=template, company=clean, domain=dom, city="Austin TX", headcount=hc,
                        signal_plain=f"Austin open data: {n} {'new residential' if new_only else 'residential building'} permits since {first}",
                        evidence_urls=["https://data.austintexas.gov/resource/3syk-w9eu"], score=min(n, 40) / 4, fields=f))
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------- win-back (11)
def years_in_business(domain):
    txt = contact.page_text(contact.fetch(f"https://{domain}/") + " " + contact.fetch(f"https://{domain}/about"))
    m = re.search(r"(?:since|established|est\.?|founded(?: in)?)\s*(19[5-9]\d|20[01]\d)", txt, re.I)
    if m:
        return datetime.date.today().year - int(m.group(1))
    m = re.search(r"(\d{2})\+?\s*(?:years|yrs)\b", txt, re.I)
    return int(m.group(1)) if m else None


def winback_candidates(exclude=(), limit=12, max_places=80):
    trades = ["roofing contractor", "HVAC company", "remodeling contractor", "landscaping company", "plumbing company", "home builder"]
    qs = [f"{t} in {c}" for c in cities(6) for t in trades]
    places, seen = [], set()
    for rows, q in zip(pmap(leads.maps, qs), qs):
        for p in rows:
            dom = leads.domain_of(p.get("website"))
            rc = p.get("review_count") or 0
            if not dom or dom in exclude or dom in seen or rc < 100 or (p.get("rating") or 0) < 4.0 or leads.CHAINS.search(p.get("name", "")):
                continue
            seen.add(dom)
            places.append((p, dom, q, rc))
    places = places[:max_places]

    def check(item):
        p, dom, q, rc = item
        revs = leads.reviews(p["place_id"], 50)
        recent = sum(1 for r in revs if leads.within_months(r.get("date"), 3))
        if recent >= 2 or not revs:
            return None
        yrs = years_in_business(dom)
        if not yrs or yrs < 10:
            return None
        return dict(service="11", template="11-review-slowdown", company=p["name"], domain=dom, city=q.split(" in ")[-1],
                    signal_plain=f"{rc} Google reviews over {yrs} years but only {recent} in the last 90 days",
                    evidence_urls=[], score=8, fields={"reviewCount": str(rc), "yearsInBusiness": str(yrs), "reviewsLast90": str(recent)})

    return [c for c in pmap(check, places, workers=4) if c][:limit]


# ---------------------------------------------------------------------------- Meta ads (13)
def ad_candidates(exclude=(), limit=15):
    out, seen = [], set()
    for kw in ["we buy houses", "sell your house fast cash", "cash offer for your house as-is"]:
        for c in cities(3, offset=3):
            city, st = c.rsplit(" ", 1)
            r = tr.call_get("scrapecreators.x.v1-facebook-adlibrary-search-ads", {"query": f"{kw} {city}", "country": "US", "status": "ACTIVE"}, max_cost=0.01)
            for ad in (r.get("searchResults") or [])[:30]:
                snap = ad.get("snapshot") or {}
                page = (snap.get("page_name") or "").strip()
                body = ((snap.get("body") or {}).get("text") or "") if isinstance(snap.get("body"), dict) else ""
                if not page or page.lower() in seen or re.search(r"opendoor|offerpad|zillow|redfin|homeVestors|we buy ugly|sell.*fast.*llc national", page, re.I):
                    continue
                if re.search(r"inherit|probate|estate sale|death|passed away|divorce|foreclos", body, re.I):
                    continue  # never probate or distress-of-a-person sourcing
                seen.add(page.lower())
                dom = None
                for pl in leads.maps(f"{page} {city} {st}")[:4]:
                    d = leads.domain_of(pl.get("website"))
                    if d and leads.name_matches(page, d, pl.get("name", "")):
                        dom = d
                        break
                if not dom or dom in exclude:
                    continue
                site = contact.page_text(contact.fetch(f"https://{dom}/"))
                if not re.search(r"buy (your |any )?(house|home)|we buy|cash offer|sell (your|my) (house|home)|as-is", site, re.I):
                    continue  # the page name matched a company that is not a house buyer (e.g. a medical firm)
                desc = "ads offering to buy houses as-is for cash" if not re.search(r"guarantee", body, re.I) else "ads offering a guaranteed cash offer on houses"
                out.append(dict(service="13", template="13-seller-leads", company=page, domain=dom, city=f"{city}, {st}",
                                signal_plain=f"Active Meta ad ({kw}) in {city}", evidence_urls=[snap.get("page_profile_uri") or ""],
                                score=7, fields={"city": city, "area": city, "adDescription": desc}))
                if len(out) >= limit:
                    return out
    return out


# ---------------------------------------------------------------------------- per-service entry points
def discover(service, exclude=(), limit=15):
    ex = set(exclude)
    if service == "01":
        qs = [f"{t} in {c}" for c in cities(6) for t in ("remodeling contractor", "home builder", "general contractor", "roofing contractor")]
        return review_candidates("01", "01-reviews", qs,
                                 r"never (called|got a call|heard|returned)|no (response|call ?back)|didn.t (return|call back|respond)|hard to reach|couldn.t get a hold|never got (a )?(quote|estimate)|stopped (responding|answering)|ignored (my|our) (calls|emails|messages)",
                                 theme="a call that never got returned", exclude=ex, limit=limit, max_places=70)
    if service == "02":
        qs = [f"{t} in {c}" for c in cities(6, 1) for t in ("emergency plumber", "HVAC repair", "emergency electrician", "garage door repair")]
        cands = review_candidates("02", "02-voicemail", qs,
                                  r"voicemail|no one answered|nobody answered|never answered|after hours|on a weekend|didn.t answer|couldn.t reach (anyone|them)|no answer",
                                  exclude=ex, limit=limit, max_places=70)
        for c in cands:  # upgrade to the approved template when the site really claims 24/7
            claim = site_claims_24_7(c["domain"])
            if claim:
                c["template"] = "02-after-hours"
                c["fields"]["hoursClaim"] = claim
                c["score"] += 3
        return sorted(cands, key=lambda c: -c["score"])
    if service == "03":
        qs = [f"{t} in {c}" for c in cities(6, 2) for t in ("custom home builder", "home builder", "home remodeling contractor")]
        a = jobs_candidates("03", "03-hiring", ["warranty coordinator custom home builder", "customer care coordinator home builder",
                                                "client experience coordinator builder", "homeowner liaison home builder"],
                            need=r"home|build|construct|warrant|homeowner", exclude=ex, limit=limit, need_company=r"home|build|construct|remodel|develop",
                            need_title=r"warrant|customer care|client (care|experience|relations)|homeowner|post.?closing|customer experience|service coordinator")
        b = review_candidates("03", "03-reviews", qs, r"no updates?|never knew what|had to (keep )?(call|chase)|lack of communication|poor communication|ghosted|stopped communicating|no communication",
                              exclude=ex, limit=limit, max_places=60)
        return a + b
    if service == "04":
        qs = [f"{t} in {c}" for c in cities(8, 3) for t in ("custom home builder", "kitchen remodeling contractor", "home remodeling contractor", "bathroom remodeling contractor")]
        return review_candidates("04", "04-change-orders", qs,
                                 r"change orders?|wrong (tile|finish|fixture|cabinets?|paint)|not what we (picked|chose|selected|ordered)|charged (us )?(extra|more)|had to (redo|replace|fix)|extra charges?",
                                 theme="change orders and extra charges", exclude=ex, limit=limit, max_places=100)
    if service == "05":
        return permit_candidates("05", "05-draws", new_only=True, exclude=ex, limit=limit)
    if service == "06":
        return permit_candidates("06", "06-permits", new_only=False, exclude=ex, limit=limit, need_team=True, lo=20, hi=250)
    if service == "08":
        return jobs_candidates("08", "08-hiring", ["accounts payable clerk construction", "accounts payable specialist contractor",
                                                   "bookkeeper construction company", "AP clerk builder"],
                               need=r"construct|contractor|builder|job cost|subcontract|project", exclude=ex, limit=limit,
                               need_title=r"payable|\bAP\b|bookkeep|accounting (assistant|clerk|specialist)", need_company=r"construct|contract|build|roof|electric|plumb|hvac|paving|civil|remodel|develop")
    if service == "09":
        return jobs_candidates("09", "09-hiring", ["billing coordinator construction", "accounts receivable clerk contractor",
                                                   "AR specialist construction company", "billing specialist roofing"],
                               need=r"construct|contractor|builder|job|project|subcontract", exclude=ex, limit=limit,
                               need_title=r"billing|receivable|\bAR\b|collections|invoic", need_company=r"construct|contract|build|roof|electric|plumb|hvac|paving|civil|remodel|develop")
    if service == "11":
        return winback_candidates(exclude=ex, limit=limit)
    if service == "13":
        return ad_candidates(exclude=ex, limit=limit)
    if service == "16":
        out = []
        for c in jobs_candidates("16", "16-reporting", ["reporting analyst", "business intelligence analyst", "data reporting analyst", "BI analyst"],
                                 days=45, exclude=ex, limit=limit * 2, min_hc=20, max_hc=250,
                                 need=r"report|dashboard|kpi|analy", need_title=r"report|\bBI\b|business intelligence|data analyst", industry_ok=r"health|hospital|bank|credit|financ|construct|manufactur|transport|logistic|non-?profit|retail|wholesale|real estate|food|energy|utilit"):
            k = kpi_line(c.get("industry"))
            if k:
                c["fields"]["kpiLine"] = k
                out.append(c)
        return out[:limit]
    return []
