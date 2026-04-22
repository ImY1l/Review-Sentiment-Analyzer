from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from typing import Dict, Any

class SentimentData(BaseModel):
    name: str  # 'Positive', 'Neutral', 'Negative'
    value: int  # percentage 0-100

class RatingData(BaseModel):
    rating: str  # '5 Stars'
    count: int
    percentage: float

class TrendData(BaseModel):
    month: str  # 'Sep'
    rating: float

class AnalysisReport(BaseModel):
    id: str
    product_id: str
    user_id: str
    summary: str
    pros: List[str]
    cons: List[str]
    sentiment_data: List[SentimentData]
    rating_data: List[RatingData]
    avg_rating: float
    recommend_rate: float
    total_reviews: int
    verified_percentage: float
    created_at: datetime
    platforms: List[str]

    class Config:
        from_attributes = True
