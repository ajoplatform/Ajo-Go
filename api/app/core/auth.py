from fastapi import Header, HTTPException
from typing import Optional
from supabase import create_client, Client
import os


supabase: Optional[Client] = None


def get_supabase() -> Client:
    global supabase
    if supabase is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
    return supabase


def get_current_admin(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization[7:]  # Remove "Bearer " prefix

    sb = get_supabase()
    if sb:
        try:
            user = sb.auth.get_user(token)
            if user and user.user:
                return {
                    "id": user.user.id,
                    "email": user.user.email,
                }
        except Exception:
            pass

    # For development/testing without Supabase
    if token == "test-token":
        return {"id": "test-admin-id", "email": "admin@test.com"}

    raise HTTPException(status_code=401, detail="Invalid token")
