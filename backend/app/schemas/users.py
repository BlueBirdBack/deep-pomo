"""User schemas"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user model"""

    username: str
    email: EmailStr


class UserCreate(UserBase):
    """User creation model"""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update model"""

    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)


class User(UserBase):
    """User model"""

    id: int
    created_at: datetime

    # Replace the class Config with this:
    model_config = ConfigDict(from_attributes=True)


class UserInDB(User):
    """User in database model"""

    password_hash: str


class Token(BaseModel):
    """Token model"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model"""

    username: Optional[str] = None
