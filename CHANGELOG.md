# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] — 2026-04-18

### Added
- Full Django 6 + Wagtail CMS project structure
- django-allauth for authentication (email/password)
- New models: SavingsGroup, GroupMember, Contribution, Payout, ReminderRule, ReminderState, Post

### Changed
- Migrated from nanodjango single-file to full Django project
- Renamed `Member` model to `GroupMember`

### Note
- FastAPI layer still present, needs model name updates for new Django models

## [0.2.0] — 2026-04-17

### Added
- FastAPI REST API layer with all CRUD endpoints
- Groups, Members, Contributions, Payouts, Cron, WhatsApp Import endpoints
- Supabase auth with JWT validation
- Dev mode test-token fallback for local development
- End-to-end pytest test suite (50 tests)

### Changed
- Unified project: merged nano and api branches into main

## [0.1.1] — 2026-04-16

### Added
- Single-file Django admin with nanodjango for local dev/ prototyping
- Admin, Group, Member, Contribution, ReminderRule, ReminderState, Payout models
- Full Django admin UI with list views, search, filters, and fieldsets
- Database schema SQL for Supabase PostgreSQL
- New dependencies: nanodjango, dj-database-url

## [0.1.0] — 2026-04-07

### Added
- DESIGN.md — approved product design (WhatsApp-first minimal MVP)
- TEST_PLAN.md — full test specification (8 test suites)
- CLAUDE.md — project context and skill routing rules
