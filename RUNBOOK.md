# Signal cold email: runbook (updated 2026-11-11)

Everything runs in the cloud. No laptop needs to be on, and any computer with your logins can operate it.
The skill (SKILL.md), scripts, templates, playbooks and this runbook all live in ONE place: this GitHub repo.

## One source of truth
- Repo: https://github.com/aydendrew-web/cold-signal-email (public, no secrets in it).
- The daily routine clones branch `main`, so `main` is the live version: work on a `dev` branch and merge to `main` only when tested. The tag `stable` is only what the Graphed reply agent downloads (playbooks, campaigns.json).
- Edit only in the repo. Do not edit copies in Drive, in the Graphed project, or in the routine prompt.
- On any computer: `git clone https://github.com/aydendrew-web/cold-signal-email.git ~/Desktop/signal-lead-scripts`, then
  `ln -s ~/Desktop/signal-lead-scripts ~/.claude/skills/signal-cold-email` so Claude Code finds the skill. Update with `git pull`.

## Change something (the only workflow)
1. Edit on a `dev` branch, test locally (`python3 finder.py <service> --target 2` costs a few cents).
2. `git add -A && git commit -m "..." && git push origin dev`.
3. When tested and you want the cloud to use it: merge `dev` into `main` and push. If playbooks or campaigns.json changed, also `git tag -f stable && git push -f origin stable`.
4. If you changed an email template: `python3 gen_playbooks.py playbooks`, commit, move `stable`, then
   `INSTANTLY_API_KEY=... python3 sync_campaigns.py --apply` (campaign text) and, in the Graphed project,
   `graphed exec -- npx tsx scripts/setup-campaigns.ts` (reply playbooks). `sync_campaigns.py --check` shows drift without changing anything.
Roll back: `git tag -f stable <older commit> && git push -f origin stable`.

## What runs where
| Piece | Where | Open it |
|---|---|---|
| Daily job "Signal cold email daily (9am Pacific)" | Claude cloud routine | https://claude.ai/code/routines/trig_018wPfVhxbPxPZZXt7oMoqKR |
| Its secrets (INSTANTLY_API_KEY, TREG_TOKEN) | "Ai Agency" cloud environment | claude.ai/code, cloud icon above the message box, Ai Agency, edit |
| Its code and instructions | Branch `main` of this repo | Cloned fresh every run |
| Daily logs | Google Drive: Cold Email Signal Email / daily logs | One file per day |
| Alerts | Gmail, subject starts "[Signal cold email]", plus a phone push | Address is set in the routine prompt |
| 14 ongoing campaigns "SCE | <template> | <service>" | Instantly | app.instantly.ai |
| Reply agent (checks Instantly every 10 min) | Graphed cloud, project signal-reply-agent | Graphed app, /outbound |
| Senders | hector@, jared@, ayden@apph2iautomation.com | |

## Current state (2026-11-13)
- Routine: ENABLED, prompt line 1 says LIVE, runs 9am Pacific (cron `0 17 * * *`). It ran LIVE on 2026-11-13 and added 4 leads (old code, cap 45).
- Since 2026-11-13: cap 120, Tier C fill (11-intro, creates its own Instantly campaign), catch-all emails accepted and tagged, service 10 discovery
  (its wording is still unapproved, so those leads are logged and not sent), 30 sends per inbox (3 inboxes = 90, so 120 needs a 4th).
- Run the finders in the background (`run_finders.py` takes up to about an hour in waves): a foreground tool call times out at 10 minutes.
- Not done: the Graphed reply agent has no playbook registered for the 11-intro campaign yet (`graphed exec -- npx tsx scripts/setup-campaigns.ts`).

## Go live (in order)
1. Run the routine once (Run now) and read the day's file in "daily logs". Check the leads and emails.
2. Edit the routine prompt: change DRY_RUN to LIVE on line 1, switch the routine ON. It then runs at 9am Pacific (17:00 UTC).
3. Switch replies to Auto-send: Graphed /outbound, each SCE campaign, Configure auto-response. Or
   `graphed exec -- npx tsx scripts/setup-campaigns.ts send` in the signal-reply-agent project.
4. Watch the first three mornings and your alert email.

## Pause or stop
- New leads: turn the routine OFF. Sending: pause the SCE campaigns in Instantly. Replies: set campaigns to Off in Graphed.

## Protections
- Daily cap 120 leads (needs enough warm inboxes: 30 sends per inbox per day (Ayden, 2026-11-13), so 3 inboxes carry at most 90; 120 needs a 4th inbox). The routine alerts and stops itself if a run spends over $10 (about $0.07 a lead, so 120 leads is about $8). Treg calls capped at $0.05 each. The routine also stops itself if
  bounces pass 5%, or a setup check fails. Only approved templates are added in LIVE mode (`services.approved_templates()`).
- Treg auto top-up is on ($20 under $5, up to $2,000 a month): lower it before running unattended.
- Instantly plan had about 990 lead uploads left on 2026-11-10.

## Chores
- About 2027-03-08 (daylight saving): change the routine's cron from `0 17 * * *` to `0 16 * * *`.
- Rotate the Instantly API key (it was pasted in chat on 2026-11-09). Update it in the Ai Agency environment and with
  `graphed secrets set INSTANTLY_API_KEY`. TREG_TOKEN is the full treg account token; swapping it for a capped agent token
  (`treg org agent-new <name> --cap 1500`) is safer.

## Off for now
Services 07 (manual only), 12, 14, 15 (no video). Templates flagged `new_wording` (10-social-video, 02-voicemail) are never added to
live campaigns until Ayden approves the wording.
