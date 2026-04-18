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
- **Database**: SQLite (dev) / PostgreSQL (prod)