# AjoGo — Digital Savings & Thrift Platform

Built with: FastAPI + Supabase + Vercel + Twilio WhatsApp API

## Overview

A WhatsApp-first thrift/cooperative management platform for West African markets (ajo/esusu tradition). Admin gets a web dashboard; members receive WhatsApp notifications. No member app needed.

Target user: Reghie — runs "Reghie Collections" thrift business with 10 groups (~50 people).

## Project Structure

```
api/                    # FastAPI backend
  app/
    api/               # Route handlers
    core/              # Config, security
    db/                # Database models & migrations
    services/          # Business logic
    whatsapp/          # Twilio WhatsApp integration
  tests/               # Unit + integration tests
  e2e/                 # End-to-end tests
frontend/              # (planned)
```

## Key Decisions

- Payout cycle: rotating (auto-detect completion + admin manual override)
- Auth: Supabase magic link by email
- Cron: Vercel Cron Jobs (every 15 min) calling `/api/cron/send-reminders`
- WhatsApp import: regex parser with confidence scoring + admin review UI
- Payments: Phase 2 (MVP is reminders + record-keeping only)

## Data Model

- `Group` — thrift group with contribution_amount, payout_schedule, current_cycle_number
- `Member` — member with phone, name, rotation_order
- `Contribution` — contribution record with source ('manual' | 'whatsapp_import')
- `ReminderState` — tracks reminder state per cycle for idempotency
- `Payout` — payout history per cycle

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health

## Testing

Run: `pytest tests/ -v`

See [TEST_PLAN.md](TEST_PLAN.md) for the full test plan.

## References

- [DESIGN.md](DESDESIGN.md) — approved product design
- [TEST_PLAN.md](TEST_PLAN.md) — test specification

## Deploy Configuration (configured by /setup-deploy)

- **Platform:** Vercel
- **Production URL:** `https://your-project-name.vercel.app` (create at vercel.com)
- **Deploy workflow:** Auto-deploy on push to main
- **Deploy status command:** HTTP health check at `/health`
- **Merge method:** squash
- **Project type:** API (FastAPI)
- **Post-deploy health check:** GET `/health`

### Vercel Cron Jobs

- **Reminders:** Runs every 15 minutes at `/api/cron/send-reminders`
- Cron secret: Set `CRON_SECRET` env var in Vercel dashboard
- Pass via header: `X-Cron-Secret: <your-secret>`

### Environment Variables (set in Vercel dashboard)

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `DATABASE_URL` | PostgreSQL connection string (from Supabase) |
| `CRON_SECRET` | Secret for cron endpoint auth |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | Twilio WhatsApp phone number |

### Deploy Commands

```bash
# Local development
cd api && pip install -r requirements.txt
python -m uvicorn main:app --reload

# Deploy (after connecting repo at vercel.com)
git push origin main
```
