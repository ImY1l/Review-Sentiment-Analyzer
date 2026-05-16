try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass
import os
from fastapi import FastAPI, Path, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from bson import ObjectId

from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from app.services.ai_service import analyze_reviews

from app.database import (
    users_collection,
    products_collection,
    platforms_collection,
    reviews_collection,
    analysis_collection,
    configs_collection,
    logs_collection,
)

LEVELS = {"info", "warning", "error", "success"}


def record_log(*, level: str, action: str, details: str, user: str | None = None):
    if level not in LEVELS:
        level = "info"
    doc = {
        "level": level,
        "action": action,
        "details": details,
        "user": user,
        "timestamp": datetime.utcnow(),
    }
    try:
        logs_collection.insert_one(doc)
    except Exception:
        # Avoid breaking core user flows if logging fails
        pass


app = FastAPI(title="Reviews Analyzer API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    # Find user by username
    user = users_collection.find_one({"username": request.username})

    if not user:
        record_log(
            level="error",
            action="login",
            details="Invalid credentials",
            user=request.username,
        )
        return {"success": False, "message": "Invalid credentials"}

    # Verify password
    if not pwd_context.verify(request.password, user["password"]):
        record_log(
            level="error",
            action="login",
            details="Invalid credentials",
            user=request.username,
        )
        return {"success": False, "message": "Invalid credentials"}

    record_log(
        level="success",
        action="login",
        details="Login successful",
        user=request.username,
    )

    return {
        "username": user["username"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    username: str
    password: str

@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    # DEBUG: log incoming payload + duplicate-check outcome
    record_log(
        level="info",
        action="register_payload",
        details=f"register payload username={user_data.username} email={user_data.email}",
        user=user_data.username,
    )

    # Check if user exists
    existing = users_collection.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing:
        matched_username = existing.get("username") == user_data.username
        matched_email = existing.get("email") == user_data.email
        if matched_username:
            msg = "Username already exists"
        elif matched_email:
            msg = "Email already exists"
        else:
            msg = "Username or email already exists"

        record_log(
            level="error",
            action="register_duplicate",
            details=f"duplicate found matched_username={matched_username} matched_email={matched_email} existing_username={existing.get('username')} existing_email={existing.get('email')}",
            user=user_data.username,
        )

        return {"success": False, "message": msg}

    # Hash password
    password_safe = user_data.password[:72] if len(user_data.password) > 72 else user_data.password
    hashed_password = pwd_context.hash(password_safe)

    # Create user
    user = {
        "name": user_data.name,
        "email": user_data.email,
        "username": user_data.username,
        "password": hashed_password,
        "role": "user",
        "createdAt": datetime.utcnow()
    }

    result = users_collection.insert_one(user)

    record_log(
        level="success",
        action="register_insert",
        details=f"inserted_id={str(result.inserted_id)} username={user_data.username}",
        user=user_data.username,
    )

    return {"success": True, "message": "User created successfully"}


@app.get("/")
async def root():
    return {"message": "Reviews Analyzer Backend API - Ready!"}

from typing import List
from pydantic import BaseModel
import asyncio
from app.scrapers.lazada_scraper import scrape_lazada
from app.scrapers.amazon_scraper import scrape_amazon_reviews as scrape_amazon
from app.scrapers.shopee_scraper import scrape_shopee as scrape_shopee
from app.scrapers.google_scraper import scrape_google
from app.scrapers.tripadvisor_scraper import scrape_tripadvisor_reviews as scrape_tripadvisor
from app.scrapers.yelp_scraper import scrape_yelp_reviews as scrape_yelp

class ScrapeRequest(BaseModel):
    query: str
    user_id: str

@app.post("/api/scrapers/lazada")
async def scrape_lazada_api(request: ScrapeRequest):
    """
    Scrape Lazada reviews for product query.
    """
    from app.scrapers.lazada_scraper import scrape_lazada
    try:
      return await scrape_lazada(request.query, request.user_id)
    except Exception as e:
      return {"success": False, "product_id": None, "message": str(e)}


@app.post("/api/scrapers/amazon")
async def scrape_amazon_api(request: ScrapeRequest):
    """
    Scrape Amazon reviews for product query.
    """
    from app.scrapers.amazon_scraper import scrape_amazon
    try:
      return await scrape_amazon(request.query, request.user_id)
    except Exception as e:
      return {"success": False, "product_id": None, "message": str(e)}

@app.post("/api/scrapers/shopee")
async def scrape_shopee_api(request: ScrapeRequest):
    """
    Scrape Shopee reviews for product query.
    """
    from app.scrapers.shopee_scraper import scrape_shopee
    try:
      return await scrape_shopee(request.query, request.user_id)
    except Exception as e:
      return {"success": False, "product_id": None, "message": str(e)}

class SearchRequest(BaseModel):
    query: str
    user_id: str
    platforms: List[str] = ["lazada"]

@app.post("/api/search")
async def unified_search(request: SearchRequest):
    record_log(
        level="info",
        action="search",
        details=f"Search started: {request.query}; platforms={request.platforms}; user_id={request.user_id}",
        user=request.user_id,
    )


    """
    Unified search: scrape selected platforms concurrently,
    aggregate reviews, analyze with AI, return results.
    """
    product_ids = []
    platforms_scraped = []


    for platform in request.platforms:
        if platform.lower() == 'lazada':
            result = await scrape_lazada(request.query, request.user_id)
            if result.get('success') and result.get('product_id'):
                product_ids.append(result['product_id'])
                platforms_scraped.append('lazada')

        elif platform.lower() == 'amazon':
            result = await scrape_amazon(request.query, request.user_id)
            if result.get('success') and result.get('product_id'):
                product_ids.append(result['product_id'])
                platforms_scraped.append('amazon')

        elif platform.lower() == 'shopee':
            result = await scrape_shopee(request.query, request.user_id)
            if result.get('success') and result.get('product_id'):
                product_ids.append(result['product_id'])
                platforms_scraped.append('shopee')

        elif platform.lower() == 'google_maps':
            result = await scrape_google(request.query, request.user_id, 'location')
            if result.get('success') and result.get('product_id'):
                    product_ids.append(result['product_id'])
                    platforms_scraped.append('google_maps')

        elif platform.lower() == 'tripadvisor':
            result = await scrape_tripadvisor(request.query, request.user_id)
            if result.get('success') and result.get('product_id'):
                product_ids.append(result['product_id'])
                platforms_scraped.append('tripadvisor')

        elif platform.lower() == 'yelp':
            result = await scrape_yelp(request.query, request.user_id)
            if result.get('success') and result.get('product_id'):
                product_ids.append(result['product_id'])
                platforms_scraped.append('yelp')

    if not product_ids:
        return {"success": False, "message": "No products scraped from any platform"}

    # Analyze all reviews together (multi-platform)
    analysis = analyze_reviews(product_ids, request.user_id)
    if not analysis:
        return {"success": False, "message": "Analysis failed"}

    # Increment user's search count once per successful unified search.
    # request.user_id from frontend is a username (e.g. "sshh"), not necessarily a MongoDB ObjectId.
    # Try increment by Mongo _id first, then fall back to username.
    try:
        users_collection.update_one(
            {"_id": ObjectId(request.user_id)},
            {"$inc": {"searchCount": 1}},
        )
    except Exception:
        pass

    try:
        users_collection.update_one(
            {"username": request.user_id},
            {"$inc": {"searchCount": 1}},
        )
    except Exception:
        pass



    return {
        "success": True,
        "product_id": product_ids[0],
        "product_ids": product_ids,
        "platforms": platforms_scraped,
        "analysis": analysis
    }


# AI Analysis endpoints
@app.post("/api/analyze/{product_id}")
async def api_analyze(product_id: str):
    user_id = "anonymous"
    """Trigger AI analysis for scraped reviews"""
    record_log(
        level="info",
        action="analysis",
        details=f"Analysis started for product_id={product_id}",
        user=user_id,
    )

    result = analyze_reviews(product_id, user_id)
    if result is None:
        record_log(
            level="error",
            action="analysis",
            details=f"Analysis failed for product_id={product_id}",
            user=user_id,
        )
        return {"success": False, "message": "No reviews found or analysis failed"}

    record_log(
        level="success",
        action="analysis",
        details=f"Analysis completed for product_id={product_id}",
        user=user_id,
    )
    return result


@app.get("/api/product/{product_id}/name")
async def api_product_name(product_id: str):
    """Get product name/title from the products collection."""
    product = products_collection.find_one({"product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Prefer common naming fields used by scrapers.
    name = product.get("name") or product.get("product_title") or product.get("product_name") or product.get("product_query")
    if not name:
        name = product_id
    return {"success": True, "product_id": product_id, "name": name}


@app.get("/api/history")
async def api_history(user_id: str = "anonymous"):

    reports = list(
        analysis_collection.find(
            {"user_id": user_id},
            projection={
                "_id": 1,
                "product_id": 1,
                "platforms": 1,
                "summary": 1,
                "avg_rating": 1,
                "created_at": 1,
            },
        ).sort("created_at", -1).limit(10)
    )

    for r in reports:
        r["report_id"] = str(r.pop("_id"))
        # Ensure created_at is JSON-serializable
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()

    # Inject product name for each report (MUST be present and non-empty for frontend sidebar)
    for r in reports:
        product_id = r.get("product_id")
        product = products_collection.find_one({"product_id": product_id})

        # products_collection documents (per your example) store the display title in `name`.
        # Frontend history sidebar MUST render `item.name`, so we set it from products `name`.
        r["name"] = (product.get("name") or "").strip() if product else ""

        # If for any reason `name` is missing/empty, keep it non-empty but do NOT fallback to analysis fields.
        if not r["name"]:
            r["name"] = "Unknown Product"

    return {"success": True, "items": reports}



# ============================================================================
# ADMIN APIs - User Management
# ============================================================================

from pydantic import BaseModel
from typing import Any

class AdminUserCreate(BaseModel):
    name: str
    email: EmailStr
    username: str
    password: str
    role: str = "user"
    dateJoined: str | None = None
    searchCount: int | None = 0


class AdminUserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    username: str | None = None
    dateJoined: str | None = None
    searchCount: int | None = None

@app.get("/api/admin/users")
async def api_admin_users():
    users = []
    cursor = users_collection.find({})
    for u in cursor:
        created_at = u.get("createdAt") or u.get("created_at")
        if isinstance(created_at, datetime):
            created_str = created_at.date().isoformat()
        else:
            created_str = str(created_at) if created_at else ""

        users.append(
            {
                "id": str(u.get("_id")) if u.get("_id") is not None else "",
                "name": u.get("name", ""),
                "email": u.get("email", ""),
                "username": u.get("username", ""),
                "dateJoined": created_str,
                "searchCount": int(u.get("searchCount", 0) or 0),
                "role": u.get("role", "user"),
            }
        )

    # Frontend expects User[] without role/searchCount optional; it will ignore extra fields.
    return [
        {
            "id": x["id"],
            "name": x["name"],
            "email": x["email"],
            "username": x["username"],
            "dateJoined": x["dateJoined"],
            "searchCount": x["searchCount"],
        }
        for x in users
    ]

@app.post("/api/admin/users")
async def api_admin_create_user(user_data: AdminUserCreate):
    # If frontend validation fails, FastAPI returns 400 without showing details in the server console.
    # This record helps us identify which field caused the error.
    record_log(level="info", action="admin_create_user_payload", details=f"payload username={user_data.username} email={user_data.email} role={getattr(user_data, 'role', None)}")

    existing = users_collection.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    createdAt = datetime.utcnow()
    password_safe = user_data.password[:72] if len(user_data.password) > 72 else user_data.password
    hashed_password = pwd_context.hash(password_safe)

    user_doc: dict[str, Any] = {
        "name": user_data.name,
        "email": user_data.email,
        "username": user_data.username,
        "password": hashed_password,
        "role": user_data.role,
        "createdAt": createdAt,
        "searchCount": int(user_data.searchCount or 0),
    }


    result = users_collection.insert_one(user_doc)

    return {
        "id": str(result.inserted_id),
        "name": user_data.name,
        "email": user_data.email,
        "username": user_data.username,
        "dateJoined": createdAt.date().isoformat(),
        "searchCount": int(user_data.searchCount or 0),
        "role": user_data.role,
    }


@app.put("/api/admin/users/{user_id}")
async def api_admin_update_user(user_id: str = Path(...), user_data: AdminUserUpdate = ...):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    update_fields: dict[str, Any] = {}
    if user_data.name is not None:
        update_fields["name"] = user_data.name
    if user_data.email is not None:
        update_fields["email"] = user_data.email
    if user_data.username is not None:
        update_fields["username"] = user_data.username
    if user_data.searchCount is not None:
        update_fields["searchCount"] = int(user_data.searchCount)

    # dateJoined is derived from createdAt in this app; ignore if provided.

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    res = users_collection.update_one({"_id": oid}, {"$set": update_fields})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated = users_collection.find_one({"_id": oid})
    created_at = updated.get("createdAt") or updated.get("created_at")
    created_str = created_at.date().isoformat() if isinstance(created_at, datetime) else str(created_at) if created_at else ""

    return {
        "id": str(updated.get("_id")),
        "name": updated.get("name", ""),
        "email": updated.get("email", ""),
        "username": updated.get("username", ""),
        "dateJoined": created_str,
        "searchCount": int(updated.get("searchCount", 0) or 0),
    }

@app.delete("/api/admin/users/{user_id}")
async def api_admin_delete_user(user_id: str = Path(...)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    res = users_collection.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True}


@app.get("/api/admin/logs")
async def api_admin_logs(level: str = "all", limit: int = 50, offset: int = 0):
    if level not in LEVELS and level != "all":
        level = "all"

    query = {}
    if level != "all":
        query = {"level": level}

    cursor = logs_collection.find(query).sort("timestamp", -1).skip(offset).limit(limit)
    results = []
    for log in cursor:
        log_id = str(log.get("_id")) if log.get("_id") is not None else None
        ts = log.get("timestamp")
        ts_str = ts.isoformat() if isinstance(ts, datetime) else (str(ts) if ts is not None else "")

        results.append(
            {
                "id": log_id or "",
                "timestamp": ts_str,
                "level": log.get("level"),
                "action": log.get("action"),
                "details": log.get("details"),
                "user": log.get("user"),
                # For frontend compatibility: map action->message if message absent
                "message": log.get("action") or log.get("details") or "",
            }
        )

    return results



@app.get("/api/results/{product_id}")
async def api_results(product_id: str):

    """Get latest analysis report for product"""
    report = analysis_collection.find_one(
        {"product_id": product_id},
        sort=[("created_at", -1)]
    )
    if not report:
        raise HTTPException(status_code=404, detail="No analysis found")
    report["_id"] = str(report["_id"])
    return report


# ============================================================================
# ADMIN APIs - Review Sources
# ============================================================================

class AdminSourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    status: str | None = None  # 'available' | 'unavailable'
    apiLimit: int | None = None


def _format_source(doc: dict) -> dict:
    source_id = str(doc.get("_id")) if doc.get("_id") is not None else str(doc.get("id") or "")

    status = doc.get("status") or "available"
    if status not in {"available", "unavailable"}:
        status = "available"

    last_checked = doc.get("lastChecked") or doc.get("last_checked") or ""
    if isinstance(last_checked, datetime):
        last_checked = last_checked.isoformat(sep=" ")

    api_limit = int(doc.get("apiLimit") or doc.get("api_limit") or 0)
    api_used = int(doc.get("apiUsed") or doc.get("api_used") or 0)
    avg_resp = doc.get("avgResponseTime") or doc.get("avg_response_time") or "N/A"

    return {
        "id": source_id,
        "name": doc.get("name") or "",
        "url": doc.get("url") or "",
        "status": status,
        "lastChecked": last_checked,
        "apiLimit": api_limit,
        "apiUsed": api_used,
        "avgResponseTime": str(avg_resp),
    }


@app.get("/api/admin/sources")
async def api_admin_sources():
    # Primary: review_platforms collection
    sources = []
    try:
        cursor = platforms_collection.find({})
        for doc in cursor:
            sources.append(_format_source(doc))
    except Exception:
        sources = []

    # Secondary fallback: configs collection (if review_platforms is empty)
    if not sources:
        try:
            cursor = configs_collection.find({})
            for doc in cursor:
                sources.append(_format_source(doc))
        except Exception:
            sources = []

    return sources


@app.put("/api/admin/sources/{source_id}")
async def api_admin_update_source(source_id: str, update: AdminSourceUpdate):
    try:
        oid = ObjectId(source_id)
    except Exception:
        # allow string-based _id if stored as plain string
        oid = None

    update_fields: dict[str, Any] = {}
    if update.name is not None:
        update_fields["name"] = update.name
    if update.url is not None:
        update_fields["url"] = update.url
    if update.status is not None:
        update_fields["status"] = update.status if update.status in {"available", "unavailable"} else "available"
    if update.apiLimit is not None:
        update_fields["apiLimit"] = int(update.apiLimit)

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Update in platforms_collection first, then configs_collection
    updated = None
    if oid is not None:
        res = platforms_collection.update_one({"_id": oid}, {"$set": update_fields})
        if res.matched_count:
            updated = platforms_collection.find_one({"_id": oid})

    if updated is None:
        res = configs_collection.update_one({"_id": oid} if oid is not None else {"id": source_id}, {"$set": update_fields})
        if res.matched_count:
            updated = configs_collection.find_one({"_id": oid} if oid is not None else {"id": source_id})

    if not updated:
        raise HTTPException(status_code=404, detail="Source not found")

    return _format_source(updated)


@app.post("/api/admin/sources/{source_id}/check")
async def api_admin_check_source(source_id: str):
    # Lightweight check: just validate key env is present if url hints SerpApi/Gemini
    # and set lastChecked; real scraping verification is done during actual search.
    start = datetime.utcnow()

    source_doc = None
    try:
        try:
            oid = ObjectId(source_id)
            source_doc = platforms_collection.find_one({"_id": oid}) or configs_collection.find_one({"_id": oid})
        except Exception:
            source_doc = platforms_collection.find_one({"id": source_id}) or configs_collection.find_one({"id": source_id})
    except Exception:
        source_doc = None

    if not source_doc:
        raise HTTPException(status_code=404, detail="Source not found")

    url = str(source_doc.get("url") or "")

    has_serpapi = bool(os.getenv("SERPAPI_KEY")) if 'serpapi' in url.lower() or 'maps' in url.lower() else bool(os.getenv("SERPAPI_KEY"))
    has_google = bool(os.getenv("GOOGLE_API_KEY"))

    # Decide status based on which key appears relevant.
    if 'serpapi' in url.lower() or has_serpapi:
        status = 'available' if has_serpapi else 'unavailable'
    else:
        status = 'available' if has_google else 'unavailable'

    elapsed_ms = (datetime.utcnow() - start).total_seconds() * 1000
    avg_response_time = f"{elapsed_ms:.0f}ms" if elapsed_ms else "N/A"

    update_fields = {
        "status": status,
        "lastChecked": datetime.utcnow().isoformat(sep=" "),
        # update usage counters conservatively
        "apiUsed": int(source_doc.get("apiUsed") or source_doc.get("api_used") or 0),
        "avgResponseTime": avg_response_time,
    }

    try:
        platforms_collection.update_one({"_id": source_doc.get("_id")}, {"$set": update_fields})
    except Exception:
        try:
            configs_collection.update_one({"_id": source_doc.get("_id")}, {"$set": update_fields})
        except Exception:
            pass

    # Return updated (or fallback to formatted doc)
    updated_doc = None
    try:
        updated_doc = platforms_collection.find_one({"_id": source_doc.get("_id")}) or configs_collection.find_one({"_id": source_doc.get("_id")})
    except Exception:
        updated_doc = None

    return _format_source(updated_doc or source_doc)


