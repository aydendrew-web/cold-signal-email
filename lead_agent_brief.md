# Lead agent brief (one agent per service, lead generation only)

You find leads for ONE service. Detect the signal, qualify, find the owner/president/CEO and a VERIFIED email. Do NOT write or render emails, and do NOT touch Instantly or Gmail. Public, logged-out data only. Never include a reviewer's name.

## Tools
Python helpers in the work folder (`tr.py`, `leads.py`, `services.py`, `instantly.py`). `treg` is installed and signed in via TREG_TOKEN.
```python
import sys; sys.path.insert(0, WORK); import tr, leads, services
tr.CURRENT["service"] = "<service id>"        # tags every charge to your service
leads.review_signal(query, regex)             # reviews in the last 12 months (handles relative dates)
leads.job_signal(query, need=regex, exclude=domains)   # Indeed post -> verified company site, headcount 5-250
leads.contact(domain, owner_name=None)        # owner/CEO + verified email, returns verified=True only on 'valid'
tr.call(endpoint, data, max_cost)             # any treg endpoint; `treg catalog search "<job in plain words>"` finds more
```
One small call first, read the charge, then scale. Never pay more than $0.05 on one call. Budget: about 60 calls and $0.30 for your service. Stop at the budget and report.

## Rules that apply to every service
- US only. Skip big chains, staffing firms, franchise national pages. Company size 5 to 250 (builders and trades 5 to 50).
- A lead counts only with a `valid` email verdict. Never invent a name, email or quote. Skip catch-all verdicts.
- Look companies up by WEBSITE, not name. Name lookups often return the wrong company (seen for Gregory Construction, Frank Gay Residential, Buildlabs, Exo Group). If the returned site does not match the company name, drop it or get the site from the company's own page or a maps result.
- Owner name must be a real person. If people search returns a company string or an unrelated company, read the About/Team page and pass `owner_name` to `leads.contact`. Search `q="owner"` first.
- Exclude every domain in the exclusion list you were given. Return at most your lead target; "no leads today" with the reason is a valid answer. Never pad.
- Indeed location: use "United States" or a bare state. "City, ST" and blank often return nothing. Use the ISO `published` date, not the `posted` text.
- Post age: job posts 30 to 45 days old at most. Reviews within 12 months.
- Slow treg calls can time out; retry once. Many agents running at once can slow calls.

## Return, for each lead (JSON list)
`{service, template, company, domain, city, first_name, last_name, title, email, verdict, signal_plain, evidence_urls, fields:{<the template's per-lead fields>}, spend_usd}` plus `difficulties` for the run. `fields` must match `services.TEMPLATES[template]["fields"]`; plus `role` and `a_an` ("a"/"an") for hiring templates.

## Per-service guidance (from the 2026-11-09 test)
- 01 speed to lead (`01-reviews`, `01-ads`): lead-stage complaints are rare. Widen the regex ("never called back", "no response", "hard to reach", "never got a quote", "didn't return"), search several trades and cities, read candidates by hand. Quote under 15 words, verbatim. Ads variant: Meta ads library + a form-only site.
- 02 after-hours (`02-after-hours`): needs BOTH a "24/7 / emergency" claim on the company's own site (their words go in `hoursClaim`) and a voicemail/after-hours review. No claim, no lead. Check the site text before using it.
- 03 client updates (`03-reviews`, `03-hiring`): hiring variant works ("warranty coordinator", "customer care coordinator", "homeowner liaison" at a custom/semi-custom builder; empty location worked best). Reviews: "no updates", "had to keep calling", "ghosted after we signed".
- 04 selections/change orders (`04-change-orders`): hard. About 35 builders had no qualifying review. Try Yelp reviews (`crawl4ai.yelp.business.reviews`), more cities (Houston, Phoenix, Atlanta, Nashville). OK to return none.
- 05 draws (`05-draws`) and 06 permits (`06-permits`): free city open data, no treg. Austin: `data.austintexas.gov/resource/3syk-w9eu` (contractor_company_name, issue_date, work_class). `leads.socrata_top_contractors`. Pick a small-to-mid builder (not a national homebuilder), then its website via a maps search. Counts differ by window; state the window. 05 wants new-construction permits only. 06 needs `teamSize` (a sourced figure; if you cannot source one, do not use this template).
- 07 entities: manual only (no automated route from LLC records to an owner email). Skip.
- 08 invoice entry (`08-hiring`) and 09 payment chase (`09-hiring`): Indeed posts for AP clerk / billing coordinator / AR clerk at contractors. Use "United States", broad query ("construction billing coordinator"). Prefer posts under 45 days.
- 10 social posting (`10-social-video`): "busy but silent". Get Instagram handles by grepping the company's own site (free), then `treg.instagram.user.posts` (slow, unsorted: take the newest date). `activeWork` must come from a real source (site, permits, reviews).
- 11 win-back (`11-review-slowdown`): 100+ reviews but under 2 in the last 90 days, 10+ years in business. Rare (about 1 in 8 firms). `review_count` is in the maps row. Needs a verified owner email: try `owner_name` from the About page.
- 13 seller finder (`13-seller-leads`): Meta ads library via `scrapecreators.x.v1-facebook-adlibrary-search-ads` (the default ad search returned nothing). Use their ad's wording in `adDescription` ("ads offering as-is cash offers on houses that need repairs"), never probate or inherited-house ads. Use the state if the city is not on their site.
- 16 reporting-hiring (`16-reporting`): reporting/BI analyst posts, US, headcount 20 to 250, exclude staffing, IT, software, consulting, government, education, defense, HR and data vendors. Keep privately run businesses, credit unions, banks, health centers, nonprofits. `kpiLine` is the five numbers that owner checks, in their industry's words. Email the owner/CEO/president/COO.
