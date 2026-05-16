from pydantic import BaseModel
from typing import Literal


class SourceStatus(str):
    available: Literal['available']
    unavailable: Literal['unavailable']


class ReviewSourceOut(BaseModel):
    id: str
    name: str
    url: str
    status: Literal['available', 'unavailable']
    lastChecked: str
    apiLimit: int
    apiUsed: int
    avgResponseTime: str

