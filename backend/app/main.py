from fastapi import FastAPI
from datetime import datetime
from bson import ObjectId

from app.database import (
    users_collection,
    products_collection,
    platforms_collection,
    reviews_collection,
    analysis_collection,
    configs_collection
)

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/insert-user")
def insert_user():
    user = {
        "email": "test@example.com",
        "password": "hashed_password",
        "role": "user",
        "createdAt": datetime.utcnow()
    }
    result = users_collection.insert_one(user)
    return {"id": str(result.inserted_id)}


@app.get("/insert-product")
def insert_product():
    product = {
        "name": "iPhone 15",
        "category": "Electronics",
        "createdAt": datetime.utcnow()
    }
    result = products_collection.insert_one(product)
    return {"id": str(result.inserted_id)}


@app.get("/insert-platform")
def insert_platform():
    platform = {
        "name": "Amazon",
        "baseURL": "https://amazon.com",
        "apiKey": "N/A",
        "isActive": True
    }
    result = platforms_collection.insert_one(platform)
    return {"id": str(result.inserted_id)}


@app.get("/insert-review")
def insert_review():
    review = {
        "productId": ObjectId("69c222eef3a84e8596642a49"),
        "platformId": ObjectId("69c22441f3a84e8596642a4e"),
        "text": "Amazing phone, very fast!",
        "rating": 4.5,
        "author": "John",
        "timestamp": datetime.utcnow(),
        "qualityScore": 0.9,
        "isCredible": True
    }
    result = reviews_collection.insert_one(review)
    return {"id": str(result.inserted_id)}


@app.get("/insert-config")
def insert_config():
    config = {
        "apiKeys": {
            "gemini": "api_key_here",
            "scraper": "none"
        },
        "timeoutLimit": 5000,
        "encryptionKey": "secret",
        "updatedAt": datetime.utcnow()
    }
    result = configs_collection.insert_one(config)
    return {"id": str(result.inserted_id)}

