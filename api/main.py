from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.api import groups, members, contributions, payouts, cron, whatsapp_import
from api.app.db.database import engine
from api.app.db.models import Base


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
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok"}
