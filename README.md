# AjoGo — Digital Savings & Thrift Platform

A WhatsApp-first thrift/cooperative management platform for West African markets (ajo/esusu tradition). Built with Django 6 + Wagtail CMS.

## Quick Start

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

## Access

- Site: http://localhost:8000
- Admin: http://localhost:8000/admin
- Wagtail CMS: http://localhost:8000/cms

## Tech Stack

- **Backend**: Django 6
- **CMS**: Wagtail
- **Auth**: django-allauth
- **API**: FastAPI (uses Django ORM)
- **Database**: SQLite (dev) / PostgreSQL (prod)

## API

FastAPI runs on port 8002:

```bash
cd api && python -m uvicorn main:app --port 8002
```

Endpoints:
- `/api/groups` — CRUD for savings groups
- `/api/groups/{id}/members` — group members
- `/api/groups/{id}/contributions` — contribution records
- `/api/groups/{id}/payouts` — payout management
- `/api/groups/{id}/whatsapp-import` — WhatsApp chat import