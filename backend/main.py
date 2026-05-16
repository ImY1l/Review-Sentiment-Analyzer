try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass
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
    # Check if user exists
    existing = users_collection.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing:
        return {"success": False, "message": "Username or email already exists"}

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
        details=f"Search started: {request.query}; platforms={request.platforms}",
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

