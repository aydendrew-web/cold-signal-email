# Signal cold email: lead and send scripts (2026-11-09)

Helper scripts for the daily lead-generation routine. Python 3, standard library only (plus the `treg` CLI).

| File | What it does |
|---|---|
| `tr.py` | Calls the treg CLI, caps any single call at $0.05, logs every charge to `run/costs.csv` (`LEADS_RUN_DIR` to change the folder). |
| `leads.py` | Signal search and contact helpers: Google Maps, reviews, Indeed jobs, company lookup, `review_signal`, `job_signal`, `contact` (finds the owner/CEO and a verified email), Socrata permit counts. |
| `services.py` | The services that have a live video, their email templates, per-lead fields, video page and length. Excluded until a video exists: 12, 14, 15. 07 is manual only. |
| `render_emails.py` | Fills a template for a lead and checks it: banned words, em dashes, exclamation points, prices, unfilled fields, length, review quote length. |
| `instantly.py` | Direct Instantly API v2: create campaigns, add leads, activate or pause, count emails sent today for the daily cap. Key comes from `INSTANTLY_API_KEY`. |

## Environment variables (set in the cloud environment, never in a prompt)
- `INSTANTLY_API_KEY`: Instantly API v2 key.
- `TREG_TOKEN`: treg token for the team (`treg org agent-new`). Install the CLI first: `uv tool install --python ">=3.12,<3.14" "tools-registry[proxy]"`.

## Daily flow (what the routine does)
1. `instantly.sent_since(<today 00:00 UTC>)` for the cap. Stop at 45 a day (15 per inbox).
2. Launch one agent per active service, in parallel, for lead generation only (find signal, owner, verified email). Each returns leads with the fields its template needs.
3. The main run merges and removes duplicate domains (strongest signal wins), then `render_emails.render()` each lead. Fix or drop any lead with issues.
4. Add leads to that template's ongoing campaign (`instantly.add_leads`). Campaigns are created once with `instantly.create_campaign(*services.build(tid))` and stay open.
5. Write the dated lead file and send log. Pause a campaign and alert Ayden on a bounce spike or any API error. Never retry a send.

## Known limits
- `leads.name_matches` rejects acronym domains (for example Joseph Design Build at `jdb.homes`). Pass `owner_name` and a verified domain by hand in that case.
- Service 10 (`10-social-video`) uses new wording that Ayden has not approved yet.
- `instantly.add_leads` uses the `/leads/add` bulk endpoint; test it on one lead before relying on it.
- Instantly can take from a few seconds to several minutes to start sending after a campaign is activated.
