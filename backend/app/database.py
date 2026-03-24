from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))

db = client["review_analyzer"]

users_collection = db["users"]
products_collection = db["products"]
reviews_collection = db["reviews"]
platforms_collection = db["review_platforms"]
analysis_collection = db["analysis_reports"]
configs_collection = db["configs"]

