from google import genai
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union
from pydantic import ValidationError
from app.database import reviews_collection, products_collection, analysis_collection
from app.models.analysis import AnalysisReport, SentimentData, RatingData, TrendData
from datetime import datetime
import json
import uuid


load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def analyze_reviews(product_ids: Union[str, List[str]], user_id: str) -> Optional[Dict[str, Any]]:
    """
    Analyze scraped reviews for a product using Gemini AI.
    Accepts single product_id or list of product_ids for multi-platform analysis.
    Returns structured data matching frontend expectations.
    """
    if isinstance(product_ids, str):
        product_ids = [product_ids]
    
    # Fetch reviews and product info
    reviews = list(reviews_collection.find({"product_id": {"$in": product_ids}}))
    if not reviews:
        return None
    
    product = products_collection.find_one({"product_id": product_ids[0]})
    platforms = list(set(r.get("platform", "unknown") for r in reviews))
    
    reviews_text = "\n\n".join([
        f"Review {i+1}: Rating: {r.get('rating', 0)}/5\nComment: {str(r.get('comment', '') or '')[:1000]}\nReviewer: {r.get('reviewer_name', 'Anon')}\nDate: {r.get('date', '')}\n---"
        for i, r in enumerate(reviews)
    ])
    
    total_reviews = len(reviews)
    
    prompt = f"""
Analyze these reviews and return a JSON object with EXACTLY this structure (no extra fields):

{{
  "summary": "Concise 2-3 sentence analysis (100-150 words)",
  "pros": ["bullet 1", "bullet 2", "bullet 3", ...] (5-8 items),
  "cons": ["bullet 1", "bullet 2", ...] (3-6 items),
  "sentiment_data": [
    {{"name": "Positive", "value": 90}},
    {{"name": "Neutral", "value": 82}},
    {{"name": "Negative", "value": 12}}
  ],
  "rating_data": [
    {{"rating": "5 Stars", "count": 1250, "percentage": 50}},
    ...
  ],
  "recommend_rate": 87.5,
  "verified_percentage": 80.2
}}

Reviews ({total_reviews} total):
{reviews_text}

Rules:
- "recommend_rate" refers to the recommendation to visit/buy the place/product.
- "recommend_rate" must be a number from 0 to 100.
- "verified_percentage" refers to the percentage of how trusted the reviews are based on the tone and available information.
- "verified_percentage" must be a number from 0 to 100.
- Percentages in sentiment_data should sum ~100.
- Percentages in rating_data should sum ~100.
- Ratings must be 1-5 stars.
- The sum of all "count" values in rating_data should equal the total number of reviews.
- The sum of all "value" values in sentiment_data should equal the total number of reviews.
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

        # Create full report (verified_percentage must come from Gemini output)
        report = AnalysisReport(
            id=str(uuid.uuid4()),
            product_id=product_ids[0],
            user_id=user_id,
            summary=analysis_data["summary"],
            pros=analysis_data["pros"],
            cons=analysis_data["cons"],
            sentiment_data=[SentimentData(**s) for s in analysis_data["sentiment_data"]],
            rating_data=[RatingData(**r) for r in analysis_data["rating_data"]],
            avg_rating=round(avg_rating, 1),
            # Must be provided by Gemini (no default fallback)
            recommend_rate=float(analysis_data["recommend_rate"]),
            total_reviews=total_reviews,
            # Gemini-provided verified_percentage
            verified_percentage=float(analysis_data["verified_percentage"]),
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
