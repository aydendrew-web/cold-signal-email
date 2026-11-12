"""Direct Instantly API v2 helpers. Key comes from INSTANTLY_API_KEY (never hard-coded)."""
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://api.instantly.ai/api/v2"
# Instantly rejects Pacific time zones. America/Dawson is UTC-7 all year (no daylight saving).
TIMEZONE = "America/Dawson"


def _key():
    k = os.environ.get("INSTANTLY_API_KEY", "").strip()
    if not k:
        raise RuntimeError("INSTANTLY_API_KEY is not set")
    return k


def api(method, path, body=None, retries=2):
    # Instantly rejects an empty body when the content type is JSON (DELETE, bare POSTs): send {} instead.
    data = json.dumps(body if body is not None else {}).encode() if method != "GET" else None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            BASE + path, data=data, method=method,
            headers={"Authorization": "Bearer " + _key(), "Content-Type": "application/json", "User-Agent": "curl/8.7.1"},
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            return {"_error": f"{e.code} {e.read().decode()[:200]}"}
        except Exception as e:  # network
            if attempt < retries:
                time.sleep(3)
                continue
            return {"_error": str(e)[:200]}
    return {"_error": "unknown"}


def list_accounts():
    d = api("GET", "/accounts?limit=100")
    return [a for a in d.get("items", []) if a.get("status") == 1]


def list_campaigns():
    d = api("GET", "/campaigns?limit=100")
    return d.get("items", [])


def create_campaign(name, subject, body, senders, daily_limit=15):
    """Create a campaign (status 0 = draft, not sending). Body/subject keep Instantly merge tags."""
    days = {str(i): True for i in range(7)}
    return api("POST", "/campaigns", {
        "name": name,
        "campaign_schedule": {"schedules": [{"name": "all day", "timing": {"from": "08:00", "to": "17:00"},
                                             "days": {"0": False, "1": True, "2": True, "3": True, "4": True, "5": True, "6": False},
                                             "timezone": TIMEZONE}]},
        "sequences": [{"steps": [{"type": "email", "delay": 0, "variants": [{"subject": subject, "body": body}]}]}],
        "email_list": senders,
        "daily_limit": daily_limit,
        "text_only": True, "open_tracking": False, "link_tracking": False,
        "stop_on_reply": False, "stop_on_auto_reply": True,
    })


def add_leads(campaign_id, leads):
    """leads: [{email, first_name, last_name, company_name, custom_variables:{}}]. Skips anyone already in the workspace."""
    return api("POST", "/leads/add", {
        "campaign_id": campaign_id, "leads": leads,
        "skip_if_in_workspace": True, "skip_if_in_campaign": True, "verify_leads_on_import": False,
    })


def lead_payload(lead, run_date):
    """Instantly lead dict for a finder lead. custom_variables = the email's merge fields plus analysis tags
    (svc, template, signal, city, contactTitle, verdict, emailSource, headcount, runDate) so campaigns can be sliced later."""
    tags = {"svc": lead.get("service"), "template": lead.get("template"), "signal": (lead.get("signal_plain") or "")[:200],
            "city": lead.get("city"), "contactTitle": lead.get("title"), "verdict": lead.get("verdict"),
            "emailSource": lead.get("email_source"), "headcount": lead.get("headcount"), "runDate": run_date,
            "leadCostUsd": lead.get("spend_usd")}
    cv = {k: v for k, v in {**(lead.get("fields") or {}), **tags}.items() if v not in (None, "")}
    return {"email": lead["email"], "first_name": lead.get("first_name"), "last_name": lead.get("last_name"),
            "company_name": lead.get("company"), "website": lead.get("domain"), "custom_variables": cv}


def activate(campaign_id):
    return api("POST", f"/campaigns/{campaign_id}/activate", {})


def pause(campaign_id):
    return api("POST", f"/campaigns/{campaign_id}/pause", {})


def sent_since(iso_ts, pages=5):
    """Count emails sent since a UTC timestamp, to enforce the daily cap."""
    n, cursor = 0, None
    for _ in range(pages):
        q = f"/emails?email_type=sent&limit=100&min_timestamp_created={iso_ts}" + (f"&starting_after={cursor}" if cursor else "")
        d = api("GET", q)
        items = d.get("items", [])
        n += len(items)
        cursor = d.get("next_starting_after")
        if not cursor or not items:
            break
    return n


def unread_count():
    return api("GET", "/emails/unread/count").get("count")
