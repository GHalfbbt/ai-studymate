"""
User-related Pydantic schemas for request/response validation.

Defines the data shapes for user registration, login, and profile responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration request."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=8, description="Password (minimum 8 characters)"
    )
    full_name: Optional[str] = Field(None, description="User's display name")


class UserLogin(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserResponse(BaseModel):
    """Schema for user profile response."""
    id: UUID
    email: str
    full_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenData(BaseModel):
    """Schema for decoded token payload."""
    user_id: Optional[str] = None


class UserSettings(BaseModel):
    """Schema for user settings (GET response)."""
    llm_provider: str = Field(default="auto", description="LLM provider: auto, groq, gemini, or ollama")

    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings (PUT request)."""
    llm_provider: str = Field(
        ...,
        pattern="^(auto|groq|gemini|ollama)$",
        description="LLM provider: auto, groq, gemini, or ollama",
    )
