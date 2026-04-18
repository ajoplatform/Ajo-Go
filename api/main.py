import os
import sys
from pathlib import Path

# Add project root to path (api/ -> project root)
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "api"))

# Configure Django before importing Django models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.api import groups, members, contributions, payouts, cron, whatsapp_import


app = FastAPI(title="AjoGo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(groups.router)
app.include_router(members.router)
app.include_router(contributions.router)
app.include_router(payouts.router)
app.include_router(cron.router)
app.include_router(whatsapp_import.router)


@app.on_event("startup")
def startup():
    # Django models are managed via manage.py migrate
    pass


@app.get("/health")
def health_check():
    return {"status": "ok"}
