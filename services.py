"""Services with a live video, their email templates and per-lead fields.

Only services that have a finished training video are listed as active (Ayden, 2026-11-09).
Excluded until a video exists: 12 call scorecards, 14 Amazon listing image sets, 15 broker listing packs.
Video pages: https://www.h2iautomation.net/<slug> (HighLevel "Outbound Services" funnel). Lengths are read from the
live files and rounded to the nearest minute. 16 reporting-hiring uses /monday-numbers-page (about 6 minutes).
Templates use Instantly merge tags; <<VL>> / <<ROLEWORK>> / <<OFFER>> are filled when a campaign is built.
"""

SIGNATURE = "\n\nAyden Hector\nH2 Intelligence\n12224 NE Bel-Red Road, No. 2029, Bellevue, WA 98009"
TIME_OFFER = "saves companies like yours 20 hours a week or your money back"
DOLLAR_OFFER = "saves contractors tens of thousands of dollars a year or your money back"
ASK = "I recorded a free <<VL>> training that shows you how to build it yourself. Want me to send it over?"

# service id -> video page slug, length in seconds, active?, note
SERVICES = {
    "01": dict(name="Speed to lead", slug="speed-to-lead-page", secs=250, active=True),
    "02": dict(name="After-hours receptionist", slug="after-hours-receptionist", secs=210, active=True),
    "03": dict(name="Client updates during the build", slug="client-updates-page", secs=233, active=True),
    "04": dict(name="Selections and change orders", slug="change-orders-page", secs=215, active=True),
    "05": dict(name="Draws and lien waivers", slug="draws-and-lien-waivers-page", secs=177, active=True),
    "06": dict(name="Permit tracker", slug="permit-tracker-page", secs=195, active=True),
    "07": dict(name="Entity and filing tracker", slug="entity-filing-tracker-page", secs=177, active=False,
               reason="no automated path from LLC records to a real owner email; manual only"),
    "08": dict(name="Invoice entry", slug="invoice-entry-page", secs=179, active=True),
    "09": dict(name="Invoicing and payment chase", slug="invoicing-and-payment-chase-page", secs=169, active=True),
    "10": dict(name="Social posting from job-site photos", slug="social-posting-page", secs=199, active=True),
    "11": dict(name="Past-client follow-up and referrals", slug="past-client-follow-up-page", secs=146, active=True),
    "13": dict(name="Distressed-seller finder agent", slug="distressed-seller-finder-page", secs=177, active=True),
    "16": dict(name="Reporting-hiring (Monday numbers)", slug="monday-numbers-page", secs=360, active=True),
    "12": dict(name="Call scorecards", active=False, reason="no video yet"),
    "14": dict(name="Amazon listing image sets", active=False, reason="no video yet"),
    "15": dict(name="Broker listing packs", active=False, reason="no video yet"),
}


def video_minutes(service):
    return int(SERVICES[service]["secs"] / 60 + 0.5)


def video_url(service):
    return f"https://www.h2iautomation.net/{SERVICES[service]['slug']}"


def _hiring(rolework, offer):
    return dict(
        subject="{{role}} at {{companyName}}",
        body="Hi {{firstName}},\n\nSaw {{companyName}} is hiring {{a_an}} {{role}}. A lot of that job is " + rolework +
             ", so I built an agent that handles that part, and it " + offer + ".\n\n" + ASK,
        fields=["role", "a_an"])


# template id -> service, subject, body, per-lead fields (beyond firstName/companyName)
TEMPLATES = {
    "01-reviews": dict(service="01", fields=["reviewSource", "reviewTheme", "reviewQuote"],
        subject="{{companyName}} reviews",
        body='Hi {{firstName}},\n\nA recent {{reviewSource}} review for {{companyName}} mentions {{reviewTheme}}: "{{reviewQuote}}." '
             "Most of those are leads that reached out and didn't hear back fast enough.\n\n"
             "I built an agent that answers every inquiry in under a minute, day or night, and it " + TIME_OFFER + ". " + ASK),
    "01-ads": dict(service="01", fields=["adPlatform"],
        subject="your {{adPlatform}} ads",
        body="Hi {{firstName}},\n\nSaw {{companyName}} is running {{adPlatform}} ads, and the clicks land on a contact form with no chat or "
             "booking option. Someone who fills that out at 9pm and hears back the next afternoon has usually called another company by then.\n\n"
             "I built an agent that makes sure you never lose those leads after hours, and it " + TIME_OFFER + ". " + ASK),
    "02-after-hours": dict(service="02", fields=["hoursClaim", "reviewSource", "reviewQuote"],
        subject="after-hours calls at {{companyName}}",
        body='Hi {{firstName}},\n\n{{companyName}} advertises {{hoursClaim}}, and a recent {{reviewSource}} review says "{{reviewQuote}}." '
             "When a no-heat or leak call hits voicemail at 10pm, that job is usually booked with someone else by 10:05.\n\n"
             "I built an agent that answers every after-hours call in your name, books the routine ones and gets emergencies to your on-call "
             "tech in minutes. " + ASK),
    "02-voicemail": dict(service="02", fields=["reviewSource", "reviewQuote"], new_wording=True,
        subject="{{companyName}} reviews",
        body='Hi {{firstName}},\n\nA recent {{reviewSource}} review for {{companyName}} says "{{reviewQuote}}." '
             "When a call hits voicemail at 10pm, that job is usually booked with someone else by 10:05.\n\n"
             "I built an agent that answers every after-hours call in your name, books the routine ones and gets emergencies to your on-call "
             "tech in minutes. " + ASK),
    "03-reviews": dict(service="03", fields=["reviewSource", "reviewQuote"],
        subject="{{companyName}} reviews",
        body='Hi {{firstName}},\n\nA recent {{reviewSource}} review for {{companyName}} says "{{reviewQuote}}." '
             "Most buyers aren't upset about the build, they just haven't heard anything in a while.\n\n"
             "I built an agent that sends every buyer a plain-English update with photos at each milestone, and it " + TIME_OFFER + ". " + ASK),
    "03-hiring": None,  # filled below
    "04-change-orders": dict(service="04", fields=["reviewSource", "reviewTheme", "reviewQuote"],
        subject="{{companyName}} reviews",
        body='Hi {{firstName}},\n\nA recent {{reviewSource}} review for {{companyName}} mentions {{reviewTheme}}: "{{reviewQuote}}." '
             "That usually happens when a change gets approved in the office and never reaches the crew.\n\n"
             "I built an agent that sends every approved change to the PM, super, sub and buyer the same minute, and it " + TIME_OFFER + ". " + ASK),
    "05-draws": dict(service="05", fields=["permitCount", "permitSince", "city"],
        subject="{{permitCount}} new homes since {{permitSince}}",
        body="Hi {{firstName}},\n\n{{companyName}} has pulled {{permitCount}} new-construction permits in {{city}} since {{permitSince}}. "
             "Every draw on a build like that waits on a stack of lien waivers from subs, and the lender kicks the package back if one is missing.\n\n"
             "I built an agent that asks for waivers ten days out and builds each draw package in the lender's format, and it saves builders tens of "
             "thousands of dollars a year or your money back. " + ASK),
    "06-permits": dict(service="06", fields=["permitCount", "permitSince", "city", "teamSize"],
        subject="{{permitCount}} permits since {{permitSince}}",
        body="Hi {{firstName}},\n\n{{companyName}} has pulled {{permitCount}} permits in {{city}} since {{permitSince}}, with a team of about {{teamSize}}. "
             "That's a lot of schedules, change orders and client updates moving through a few people.\n\n"
             "I built an agent that keeps every permit, deadline and client update moving, and it " + TIME_OFFER + ". " + ASK),
    "08-hiring": None, "09-hiring": None,  # filled below
    "10-social-video": dict(service="10", fields=["socialPlatform", "lastPostAge", "activeWork"], new_wording=True,
        subject="{{companyName}} on {{socialPlatform}}",
        body="Hi {{firstName}},\n\n{{companyName}} has {{activeWork}} right now, but the last {{socialPlatform}} post was {{lastPostAge}}.\n\n"
             "I built an agent that turns your crews' job-site photos into a steady posting schedule. " + ASK),
    "11-review-slowdown": dict(service="11", fields=["reviewCount", "yearsInBusiness", "reviewsLast90"],
        subject="{{companyName}} past clients",
        body="Hi {{firstName}},\n\n{{companyName}} has {{reviewCount}} Google reviews from {{yearsInBusiness}} years of work, but only {{reviewsLast90}} "
             "in the last 90 days. Those past clients are the likeliest to hire you again or send you a neighbor, if they remember your name.\n\n"
             "I built an agent that thanks every client at the finish, asks for the review, and checks in a few times a year with a referral ask. " + ASK),
    "11-intro": dict(service="11", fields=["opener"], new_wording=True,
        subject="{{companyName}} past clients",
        body="Hi {{firstName}},\n\n{{opener}} Work for a business like that mostly comes back through past clients and the neighbors they tell.\n\n"
             "I built an agent that thanks every client at the finish, asks for the review, and checks in a few times a year with a referral ask. " + ASK),
    "13-seller-leads": dict(service="13", fields=["city", "area", "adDescription"],
        subject="seller leads in {{city}}",
        body="Hi {{firstName}},\n\nSaw {{companyName}} is running {{adDescription}} in {{city}}. Paid seller leads get expensive, and most of them have "
             "already talked to three other buyers.\n\n"
             "I built a distressed-seller finder agent that finds and contacts off-market owners in {{area}} for you, and it saves investors tens of "
             "thousands of dollars in ad spend or your money back. " + ASK),
    "16-reporting": dict(service="16", fields=["role", "a_an", "kpiLine"],
        subject="{{role}} at {{companyName}}",
        body="Hi {{firstName}},\n\nSaw {{companyName}} is hiring {{a_an}} {{role}}. A lot of that job is rebuilding the same weekly report by hand, so I "
             "built an agent that pulls {{kpiLine}} for you and emails you what moved every Monday, and it " + TIME_OFFER + ".\n\n" + ASK),
}
for tid, svc, work, offer in (
    ("03-hiring", "03", "keeping buyers updated so they don't have to call", TIME_OFFER),
    ("08-hiring", "08", "typing supplier invoices into the accounting system and coding them to jobs", TIME_OFFER),
    ("09-hiring", "09", "building invoices, chasing payments and tracking retainage", DOLLAR_OFFER),
):
    TEMPLATES[tid] = dict(service=svc, **_hiring(work, offer))


def build(template_id):
    """Template with the video length filled in (what goes into the Instantly campaign)."""
    t = TEMPLATES[template_id]
    vl = f"{video_minutes(t['service'])}-minute"
    return t["subject"], t["body"].replace("<<VL>>", vl)


def training_link(service):
    return video_url(service)


def active_templates():
    return [tid for tid, t in TEMPLATES.items() if SERVICES[t["service"]].get("active")]


def approved_templates():
    """Templates Ayden has approved (the live routine only adds leads to these). new_wording=True means not yet approved."""
    return [tid for tid in active_templates() if not TEMPLATES[tid].get("new_wording")]
