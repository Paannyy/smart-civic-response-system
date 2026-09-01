from typing import List
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    department: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]
    total: int
    limit: int
    offset: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserStatusUpdate(BaseModel):
    is_active: bool