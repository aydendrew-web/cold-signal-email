# Signal cold email: runbook (written 2026-11-10)

Everything runs in the cloud. No laptop needs to be on, and any computer with your logins can operate it.

## What runs where
| Piece | Where it lives | Open it from any computer |
|---|---|---|
| Daily lead + email job ("Signal cold email daily (9am Pacific)") | Claude cloud routine | https://claude.ai/code/routines/trig_018wPfVhxbPxPZZXt7oMoqKR |
| Its secrets (INSTANTLY_API_KEY, TREG_TOKEN) | "Ai Agency" cloud environment | claude.ai/code, cloud icon above the message box, Ai Agency, edit |
| Its scripts and brief | Google Drive: Cold Email Signal Email / scripts (2026-11-09) | The 7 files must stay shared "anyone with the link" (the routine downloads them) |
| Its daily log | Google Drive: Cold Email Signal Email / daily logs | One file per day: leads, spend, every email, problems |
| Alerts | Gmail to the alert address set in the routine prompt, subject starts "[Signal cold email]", plus a phone push | |
| 14 ongoing campaigns "SCE | <template> | <service>" | Instantly | app.instantly.ai |
| Reply agent (checks Instantly every 10 min, answers replies) | Graphed cloud, project "signal-reply-agent", account "AJ's Account" | Graphed web app, project signal-reply-agent, /outbound page |
| Senders | hector@, jared@, ayden@apph2iautomation.com (Google, warming) | |

## Current state
- Routine: DISABLED and set to DRY_RUN (finds leads, writes emails to the log, adds nothing to Instantly).
- Graphed reply agent: running every 10 minutes. All 14 campaigns are in Draft mode (replies saved, nothing sent). Test campaign is Off.
- Instantly campaigns: drafts with no leads.

## Go live (do in this order)
1. Read the latest file in "daily logs". Check the leads, the signals and the rendered emails. Fix anything odd.
2. Open the routine, edit the prompt: change the first word on line 1 from DRY_RUN to LIVE. Turn the routine ON. It then runs daily at 9am Pacific (17:00 UTC).
3. Switch the reply agent to auto-reply: Graphed web app, /outbound, open each SCE campaign, Configure auto-response, Auto-send. (Or from a terminal with the Graphed CLI: `graphed exec -- npx tsx scripts/setup-campaigns.ts send` inside the signal-reply-agent project.)
4. Watch the first three mornings' logs and your alert email.

## Pause or stop
- Stop new leads: turn the routine OFF at claude.ai/code/routines.
- Stop all sending: in Instantly, pause the SCE campaigns.
- Stop replies: Graphed /outbound, set campaigns to Off.

## Limits that protect you
- Daily cap: 45 new leads (15 per inbox). Change the number 45 in the routine prompt.
- Treg: auto top-up is on ($20 when under $5, cap $2,000/month). Lower the cap in treg before running unattended.
- The routine alerts and stops itself if treg spend passes $3 a day, bounces pass 5%, or any setup check fails.
- Instantly plan: about 990 lead uploads remained on 2026-11-10 (about 22 days at 45 a day).

## Things to do on a schedule
- Around 2027-03-08 (daylight saving starts): change the routine's cron from `0 17 * * *` to `0 16 * * *` to stay at 9am Pacific.
- Rotate the Instantly API key (it was pasted in chat on 2026-11-09). Update it in three places: the Ai Agency environment, `graphed secrets set INSTANTLY_API_KEY`, and nowhere else.
- TREG_TOKEN is the full treg account token. If you swap it for a capped agent token (`treg org agent-new <name> --cap 1500`), update only the Ai Agency environment.
- If you edit any script in Drive, the routine's checksum check will fail on purpose. Update the checksums listed in the routine prompt (setup step 1) to match, or it will alert and stop.

## Off for now
Services 07 (manual only), 12, 14, 15 (no video). 10-social-video has new wording you have not approved: the routine skips adding leads to it in LIVE mode.

## Known issues
- The first test cold email from ayden@ never arrived once (not reproduced; later sends from all three inboxes landed).
- Instantly can take seconds to minutes to start sending after a campaign is activated.
- The GitHub repo aydendrew-web/cold-signal-email holds a backup copy of the scripts. The routine does not use it (Claude could not read the private repo).
