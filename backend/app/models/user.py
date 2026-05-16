from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
  name: str
  email: EmailStr
  username: str

class UserCreate(UserBase):
  password: str

class User(UserBase):
  id: str
  role: str = 'user'
  created_at: datetime

  class Config:
    from_attributes = True

