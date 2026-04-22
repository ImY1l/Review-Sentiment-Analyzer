from google import genai
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from pydantic import ValidationError
from app.database import reviews_collection, products_collection, analysis_collection
from app.models.analysis import AnalysisReport, SentimentData, RatingData, TrendData
from datetime import datetime
import json
import uuid


load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def analyze_reviews(product_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Analyze scraped reviews for a product using Gemini AI.
    Returns structured data matching frontend expectations.
    """
    # Fetch reviews and product info
    reviews = list(reviews_collection.find({"product_id": product_id}).limit(100))  # Sample max 100
    if not reviews:
        return None
    
    product = products_collection.find_one({"product_id": product_id})
    platforms = list(set(r.get("platform", "unknown") for r in reviews))
    
    # Prepare reviews text for prompt
    reviews_text = "\n\n".join([
        f"Review {i+1}: Rating: {r.get('rating', 0)}/5\nComment: {r.get('comment', '')}\nReviewer: {r.get('reviewer_name', 'Anon')}\nDate: {r.get('date', '')}\n---"
        for i, r in enumerate(reviews[:20])  # Top 20 for prompt
    ])
    
    total_reviews = len(reviews)
    
    prompt = f"""
Analyze these product reviews and return a JSON object with EXACTLY this structure (no extra fields):

{{
  "summary": "Concise 2-3 sentence analysis (100-150 words)",
  "pros": ["bullet 1", "bullet 2", "bullet 3", ...] (5-8 items),
  "cons": ["bullet 1", "bullet 2", ...] (3-6 items),
  "sentiment_data": [
    {{"name": "Positive", "value": 72}},
    {{"name": "Neutral", "value": 18}},
    {{"name": "Negative", "value": 10}}
  ],
  "rating_data": [
    {{"rating": "5 Stars", "count": 1250, "percentage": 50}},
    ...
  ],
}}

Reviews ({total_reviews} total):
{reviews_text}

Be specific, use actual review data/themes. Percentages must sum ~100%. Ratings 1-5 stars. Trends 6 months.
"""
    
    try:
        response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"})
        raw_json = response.text.strip()
        analysis_data = json.loads(raw_json)
        
        # Compute real metrics from reviews
        ratings = [r.get('rating', 0) for r in reviews]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Create full report
        report = AnalysisReport(
            id=str(uuid.uuid4()),
            product_id=product_id,
            user_id=user_id,
            summary=analysis_data["summary"],
            pros=analysis_data["pros"],
            cons=analysis_data["cons"],
            sentiment_data=[SentimentData(**s) for s in analysis_data["sentiment_data"]],
            rating_data=[RatingData(**r) for r in analysis_data["rating_data"]],
            avg_rating=round(avg_rating, 1),
            recommend_rate=analysis_data.get("recommend_rate", 80),  # From AI or default
            total_reviews=total_reviews,
            verified_percentage=92,  # Placeholder
            created_at=datetime.utcnow(),
            platforms=platforms
        )
        
        # Save to DB
        analysis_collection.insert_one(report.model_dump())
        
        # Return frontend-friendly dict
        return {
            **report.model_dump(exclude={"id", "created_at", "platforms"}),
            "platforms": platforms
        }
        
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        print(f"AI analysis failed: {str(e)}")
        return None
