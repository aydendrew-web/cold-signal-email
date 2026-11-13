---
name: signal-cold-email
description: H2i's signal-based cold email system (2026-11-03). One method, one playbook per niche. Finds companies showing a public signal that they have the problem we solve (a job post for the role we replace, reviews about unreturned calls, ads with no booking path, permit volume against a small team, stale social), scores them, finds a verified decision-maker email, writes the email that leads with the strongest signal, stages it in Instantly (or Gmail for small test runs), and answers replies. Use whenever Ayden asks to find leads, find signals, send cold emails, "send N more", "same workflow", start outreach to a niche, or answer a reply to one of these emails, even if he doesn't name the niche or the skill.
---

# Signal-based cold email

One method for every niche. What changes per niche is **which signals to
hunt, where to find them, and the email templates**. Those live in one
playbook file per niche. Load only the playbook for the niche at hand.

## 1. Services and where their rules live

There is one method for every service. What differs per service is the **signal**, where to find it, and the **email template**.
Those live in code, in this repo, not in separate playbook files:

| What | Where |
|---|---|
| Which services are active, their video page and length | `services.py` (`SERVICES`) |
| The email templates and each template's per-lead fields | `services.py` (`TEMPLATES`) |
| How each service finds and qualifies leads | `discover.py` (one function per service) |
| How a contact and verified email is found | `contact.py` |
| Per-service tips for agents | `lead_agent_brief.md` |

Only services with a live training video are active (Ayden, 2026-11-09): 01 to 06, 08 to 11, 13 and 16. Off: 07 (manual only), 12, 14, 15
(no video yet). A template flagged `new_wording=True` has not been approved by Ayden and is never added to a live campaign.

The older niche playbooks in Drive ("Cold Email Signal Email" folder, files named "niche - ...") are background reading for people.
Nothing automated reads them, so do not edit them to change behaviour. Change `discover.py` or `services.py` instead.

## 2. The method (same for every service)

Steps 1 to 4 (lead generation) run as parallel agents, one per service (section 2a). The main run does steps 5 to 8.

1. **Detect** (`discover.py`). Pull raw signals with treg (Google Maps and reviews, Indeed, Meta ads, city permit data). One small call
   first, read the charge, then scale. Every call is capped at $0.05 and logged to `run/costs.csv` (`tr.py`).
2. **Qualify** (`discover.py`). US only, real website that matches the company name (look companies up by website, never by name alone),
   not a chain, a fitting size, and the right industry. A signal list is not a lead list.
3. **Score.** Fresher and stronger signals rank first. A company flagged by two services is a hot lead and goes to the stronger service.
4. **Contact** (`contact.py`). Owner name from the company's own website, else treg people search. Then treg email find with
   verification. If that finds nothing, try the common address formats and verify each. An email on a different domain counts only
   when it is clearly the same company. Only a "valid" verdict counts. Generic mailboxes (info@, ask@) never count.
5. **Write** (`render_emails.py`). Fill the service's template and check it: banned words, em dashes, exclamation points, prices,
   unfilled fields, length. The main run writes the emails. Do not use parallel agents for this step.
6. **Show Ayden** the template and 5 to 10 rendered emails before the first send of any new template or wording change.
7. **Send.** See section 4. In the cloud routine, leads are added to one ongoing Instantly campaign per template.
8. **Log.** One dated file per run in the Drive folder "daily logs", with spend, per-service results and every email.

## 2a. Lead generation: one parallel agent per service

Finding leads is the only part that runs in parallel. Each service has its own signal and sources and they do not depend on each other,
so launch one agent per active service at the same time.

**Main run, before the agents:** list the active services, build the exclusion list (every domain already in any campaign), and
launch one agent per service in a single step.

**Each service agent:** runs `python finder.py <service> --target 10 --out /tmp/out/svc_<service>.json --exclude /tmp/exclude.json --max-minutes 15` (or all services at once through `run_finders.py`, which runs them in waves of 4 and then fills the shortfall with Tier C).
That does steps 1 to 4 for its service only. It writes no emails and touches no Instantly or Gmail account. If it finds fewer than the
target it may keep searching by hand within its budget, following `lead_agent_brief.md`. It returns a short summary and its spend.

**Main run, after the agents:** merge the lists, drop duplicate domains (strongest signal wins, mark it hot), then write and check the
emails (step 5). Only the main run writes the lead file, the log and the suppression list. A failed agent fails alone.

## 3. Rules that apply to every niche

- Copy: `H2 intelligence/Docs/H2i-Copy-Voice-Rules.md`, with one exception
  Ayden set on 2026-11-03: cold emails **do** say "agent" ("I built an
  agent that..."). Still no automation, platform or leverage; no em dashes;
  no exclamation points; no prices; no invented proof; one ask.
- Shape (Ayden, 2026-11-03): casual and brief, 3 to 5 short sentences.
  1. The signal: "Saw {company} is hiring a ..." / "...is running Facebook ads and..."
  2. The pain in one line.
  3. "I built an agent that..." plus a short example of what it does.
  4. The ask, one of two kinds:
     - **Demo email** (something we can show: a sample dashboard, sample
       posts): attach or link the demo, then "If it's worth it to you, I'd
       love to hop on a quick call tomorrow."
     - **Video email** (everything else, including the seller-lead finder):
       "I recorded a {N}-minute video on how to build it. Want me to send it
       over?" Always state the length; videos run 2 to 5 minutes. Fill
       `videoLength` with the real length of that offer's video.
- Offer framing (Ayden, 2026-11-06):
  - **Time-saving services:** "I built an agent that ..., and it saves
    companies like yours 20 hours a week or your money back."
  - **Services that save dollars directly** (draws, entities, payment chase,
    seller leads): "... saves contractors tens of thousands of dollars a year
    or your money back." (Say investors or developers where that's who it is.)
  - **Revenue and growth services** (after-hours receptionist, past-client
    win-back, listing images, social posting): no savings claim, just the
    training.
  - In `hiring.txt` the claim is the `offerLine` field: "saves companies like
    yours 20 hours a week or your money back", or the dollars version.
  - Open question: the guarantee wording only fits a paid build we do
    together. Say so on the call and the landing page.
- Video framing (Ayden, 2026-11-06): never just "a video". Always a **free
  training they can use to build it themselves**: "I recorded a free
  {N}-minute training that shows you how to build it yourself. Want me to
  send it over?" The value is that they take the knowledge away for free.
- Lead with one signal, the strongest. Don't list everything we found.
- **Public, logged-out data only.** Mentioning a company's public business
  facts is fine ("saw you're hiring a coordinator", a short quote from a
  public review). Never mention anything inferred about a person's finances,
  health or family, and never name a reviewer.
- First email: no link, or at most one (the demo). No calendar link; the
  call ask is "I'd love to hop on a quick call tomorrow."
- Mailing address in every cold email signature.
- Suppress anyone who replied, bounced or opted out, across every campaign.
- Outreach to EU or UK people needs a lawful basis; skip them unless Ayden
  says otherwise.

## 4. Sending

**Instantly (default once inboxes are warm).** Follow
`../cold-email-deliverability/SKILL.md`: never from the primary domain,
30 sends per inbox per day (the ceiling), plain text, no open tracking, zero or one
link, verified list only.
- Templates are written with Instantly merge tags (`{{firstName}}`,
  `{{companyName}}`, plus the playbook's custom fields). Upload the leads as
  a CSV whose column names match the custom fields exactly.
- Build the campaign and leave it **paused**. Show Ayden 5 to 10 rendered
  samples with real values. Ayden launches it. Never launch, resume or
  schedule a live campaign without his explicit OK.
- Instantly can't attach files. Anything that must be seen (a sample
  dashboard) goes as one link or is offered for the reply.

**Gmail (Ayden's own Gmail, small test runs while Instantly warms).**
- Plain text through the Gmail connector `send_message`, in parallel groups
  of 10, then search `from:mailer-daemon newer_than:1h` for bounces.
- Attachments: the connector can't attach without pasting the file into the
  call, so send attachment emails through Gmail in Ayden's Chrome: compose,
  fill, attach, check recipient, subject, body and attachment, then send.

## 5. Replies (every niche)

Reply in the same thread (`create_draft` with `replyToMessageId`; never
`update_draft`, which pulls a draft out of its thread). The exception is the
"yes" replies below, which are sent automatically. The playbook has the
niche-specific "here it is" reply. These apply everywhere:

**Timing (Ayden, 2026-11-07).** Wait about 4 minutes after their reply, then
answer. Never reply instantly, and don't let it run long.

**Yes replies are sent automatically, not left as drafts (Ayden, 2026-11-07).**
When they say yes to the demo or the training, send the reply in the same
thread (`replyToMessageId`) with only a few words of copy.

Training yes (link in the body):
```
Hi {{firstName}},

Sending it over now.

{{trainingLink}}

Ayden
```

Demo yes (real screenshot attachments, no link). The Gmail connector can't
attach files, so this one goes through Gmail in Ayden's Chrome: compose,
attach the screenshots, check recipient, subject, body and attachments, then
send.
```
Hi {{firstName}},

Sending it over now.

Ayden
```

**"Did you apply?" / "Are you a candidate?"** (read their job post first)
```
Hi {{firstName}},

No application on my end. H2 Intelligence builds the {{coveredPart}} side of that role.

Here's a free training on how to set it up yourself if you want: {{trainingLink}}

Ayden
```

**"What does it cost?"** Never put a price in writing.
```
Hi {{firstName}},

It depends on how many systems are involved, so I'd rather quote it after a quick look. Do you have 15 minutes this week? https://calendly.com/h2intelreal/discovery-call

Ayden
```

**Not interested / stop emailing**
```
Understood, I won't reach out again. Thanks for letting me know.

Ayden
```
Then add their domain to the suppression list.

## Gotchas

- treg: Hunter's email endpoint bills 10x its listed price; GetLeads allows
  5 calls a day; blitzapi can be out of capacity; Crustdata cursors expire
  within minutes.
- Use the email domain from the contact row, not the website domain.
- **Catch-all emails are accepted (Ayden, 2026-11-13, volume first).** For a catch-all domain the lead gets the owner's most likely address
  (a personal address on their site, else first@domain), `verdict=accept_all`, `emailSource=catchall-guess`. At most 40% of one finder's
  leads may be catch-all. The 5% bounce alert still pauses every SCE campaign, and the weekly analysis compares `accept_all` against
  `valid` leads, so cut it back if bounces say so.
- Service 10 (social posting) now has discovery: Instagram handle from the company's site, last post 60 days to 18 months old, and 2+ new
  Google reviews in 90 days. Its template is still `new_wording` until Ayden approves it.
- (Older note) Many small-business domains are catch-all (the mail server accepts any address), so treg verify returns `accept_all` and the lead is
  dropped with reason "catch-all domain (cannot verify)". This was most of the "no valid email" drops on 2026-11-12. Accepting
  catch-all addresses is a deliverability risk (bounces over 5% pause every campaign), so it is Ayden's call. Do not change it unasked.
- Permit sources: Austin and Chicago only. Kansas City stopped updating in May 2025, Dallas in December 2025, Seattle has no contractor field.
- Windows: Python can't see `/tmp`; keep working files in the offer folder or
  the session scratchpad.

## 6. Daily cloud routine (what the scheduled job does)

The routine "Signal cold email daily (9am Pacific)" runs on claude.ai. Its prompt only sets MODE (DRY_RUN or LIVE), fetches this
repo and tells the run to follow this section. Change behaviour here or in the code, never in the prompt.

**Setup. Stop and alert if any step fails.**
1. Environment variables INSTANTLY_API_KEY and TREG_TOKEN must be set (never print them). Work in /tmp/work (the repo checkout).
2. Install treg from PyPI with `python3 -m pip install --user uv`, then `uv tool install --python 3.12 'tools-registry[proxy]'`.
   Never pipe a download into a shell. `treg balance` must work and show at least $3.
3. `python3 -c 'import instantly; print(len(instantly.list_accounts()))'` must print 3 (the three sending inboxes).

**Run.**
1. Daily cap: 120 new leads (Ayden, 2026-11-13; 30 sends per inbox, so 120 needs 4 inboxes). remaining = 120 minus emails sent today (`instantly.sent_since`). Stop if 0.
2. Exclusion list: every email domain in every campaign listed in `campaigns.json`, plus domains of leads in earlier daily logs that were actually added to Instantly (LIVE runs). Leads from DRY_RUN logs, or from runs where the add was blocked, were never emailed and are NOT excluded. Write the list to /tmp/exclude.json as a JSON list of domains.
3. Section 2a: run `python run_finders.py --exclude /tmp/exclude.json --out /tmp/out --target 10 --cap <remaining>` (one finder per active service in waves of 4 so treg is not overloaded, each with a 15 minute hard limit that always writes /tmp/out/svc_<id>.json, partial if it ran out of time; then, if the total is short of `--cap`, eight Tier C shards sized to the shortfall, written to /tmp/out/svc_tc_<k>.json). Never pad a tier A service; log why it came up short.
4. Merge, drop duplicates (a company found by two services goes to the stronger signal), drop leads without a "valid" or "accept_all" verdict, render and check every email (`render_emails.render`). Tier A first, Tier C last. Keep at most
   `remaining`, at least one per service that found one, hot leads first.
4a. **Tier C fill (Ayden approved 2026-11-12; volume first, 2026-11-13).** `run_finders.py` does this itself: if tier A leaves a shortfall it runs
   eight shards of `python finder.py 11 --tier-c --shard K --shards 8 --target M` (M = ceil(shortfall / 8)). These are fit-only leads
   (right trade, real site, 20+ reviews at 4.0+, owner email) with no signal. The email opens with one true fact from the company's own
   website (an award, the areas they serve, years in business, or family/locally owned), never a claimed signal. They use template
   `11-intro` and carry `tier=C`. Never claim a signal a Tier C lead does not have.
5. DRY_RUN: stop here. Write the emails to the log and add nothing to Instantly.
   LIVE: write the final leads to /tmp/out/final_leads.json and run `python3 add_leads_to_instantly.py --leads /tmp/out/final_leads.json --run-date <today> --cap 120` from the repo folder (it enforces approved templates and the cap, finds or creates each campaign with `instantly.ensure_campaign`, adds, activates, never retries). It uses `instantly.add_leads(...)`, which sets custom_variables = the email fields plus analysis tags: svc, template, signal, city, contactTitle, verdict, emailSource, runDate, leadCostUsd, tier), activate any campaign
   that received leads, only for templates in `services.approved_templates()`. Log leads for unapproved templates instead. Never retry a send.
6. Check that each campaign's email text still matches `services.build()` (`python sync_campaigns.py --check`) and alert on drift.
7. Write the log file to Drive. End it with a fenced ```json block named FUNNEL: one `finder.funnel_row(service, result, today)` per service (the weekly analysis reads it). Include: mode, cap, spend per service, leads per tier (A and C), every lead, every rendered email, dropped leads and why, problems.

**Alerts** (Gmail to the alert address given in the routine prompt, subject starting "[Signal cold email]"): setup failure; run spend over $10 (120 leads cost about $8); bounce rate above 5%
in 24 hours (also pause every "SCE |" campaign); any Instantly error; fewer than 3 leads in total; campaign drift.

**Hard rules.** Never put a key in a log, file or email. Never email a prospect directly: only add leads to Instantly campaigns. Never
retry a send. US only; skip EU and UK. Do not edit the repo files during a run.

## 7. Where everything lives (single source of truth)

| Thing | The one place it lives | How other places get it |
|---|---|---|
| This skill, scripts, templates, playbooks, brief | GitHub repo aydendrew-web/cold-signal-email, branch `main` | The routine downloads tag `stable`. Computers use `git pull`. The local skill folder links to the repo |
| What the routine runs | The `stable` tag | Move the tag only after a test passes: `git tag -f stable && git push -f origin stable` |
| Reply playbooks | `playbooks/` in the repo (made by `gen_playbooks.py` from `services.py`) | The Graphed project downloads them when you run its setup script |
| Email text inside Instantly campaigns | `services.py` | `sync_campaigns.py --check` reports drift, `--apply` rewrites the campaign |
| Secrets | Claude "Ai Agency" environment (INSTANTLY_API_KEY, TREG_TOKEN) and `graphed secrets` | Never in the repo or Drive |
| Run logs | Drive: Cold Email Signal Email / daily logs | Written by the routine |

**To change anything:** edit in the repo, test locally, commit, push to `main`, then move `stable` when it is ready. Do not edit copies in
Drive, in the Graphed project, or in the routine prompt.
