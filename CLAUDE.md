# AjoGo — Digital Savings & Thrift Platform

Built with: Django 6 + Wagtail CMS + PostgreSQL (planned)

## Overview

A WhatsApp-first thrift/cooperative management platform for West African markets (ajo/esusu tradition). Admin gets a web dashboard; members receive WhatsApp notifications. No member app needed.

Target user: Reghie — runs "Reghie Collections" thrift business with 10 groups (~50 people).

## Project Structure

```
config/              # Django project settings
  settings/         # base.py, dev.py, production.py
  urls.py            # URL routing (Wagtail + admin)
  wsgi.py            # WSGI entry point
apps/               # Custom Django app (thrift business logic)
  models/           # MyUser, SavingsGroup, Member, etc.
home/               # Wagtail home page app
search/             # Wagtail search app
manage.py           # Django management script
requirements.txt    # Python dependencies
```

## Migration Status

- **2025-04-17**: Migrated from nanodjango single-file to full Django + Wagtail project
- **Next**: Implement django-allauth for authentication

## Key Decisions

- CMS: Wagtail (content management for announcements, guides)
- Auth: django-allauth (email/password, social logins later)
- Payout cycle: rotating (auto-detect completion + admin manual override)
- WhatsApp: Twilio API for notifications
- Payments: Phase 2 (MVP is reminders + record-keeping only)

## Data Model (apps/models/)

- `MyUser` — custom user with phone field (extends AbstractUser)
- `SavingsGroup` — thrift group with contribution_amount, payout_schedule, current_cycle_number
- `Member` — member with phone, name, rotation_order
- `Contribution` — contribution record with source ('manual' | 'whatsapp_import')
- `ReminderState` — tracks reminder state per cycle for idempotency
- `Payout` — payout history per cycle

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run dev server
python manage.py runserver
```

Visit http://localhost:8000 for the site, http://localhost:8000/admin for Wagtail CMS.

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.

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

## References

- [DESIGN.md](DESDESIGN.md) — approved product design
- [TEST_PLAN.md](TEST_PLAN.md) — test specification