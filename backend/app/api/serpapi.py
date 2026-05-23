import os
import httpx
from fastapi import HTTPException

SERPAPI_ACCOUNT_URL = "https://serpapi.com/account.json"

async def fetch_serpapi_usage() -> dict:
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            SERPAPI_ACCOUNT_URL,
            params={"api_key": serpapi_key},
        )

    if resp.status_code >= 400:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json() or {}
    remaining = int(data.get("plan_searches_left", 0) or 0)

    return {
        "remaining": remaining,
    }
