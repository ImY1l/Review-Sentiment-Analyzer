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
    configs_collection
)

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
        return {"success": False, "message": "Invalid credentials"}
    
    # Verify password
    if not pwd_context.verify(request.password, user["password"]):
        return {"success": False, "message": "Invalid credentials"}
    
    return {
        "username": user["username"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"]
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
from app.scrapers.amazon_scraper import scrape_amazon

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

class SearchRequest(BaseModel):
    query: str
    user_id: str
    platforms: List[str] = ["lazada"]

@app.post("/api/search")
async def unified_search(request: SearchRequest):
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
    result = analyze_reviews(product_id, user_id)
    if result is None:
        return {"success": False, "message": "No reviews found or analysis failed"}
    return result

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
