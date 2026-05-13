
from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
import re

class UserRole(str, Enum):
    parent = "parent"
    child = "child"

class RegisterRequest(BaseModel):
    email: EmailStr          # automatycznie waliduje format email
    password: str
    username: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Hasło musi mieć minimum 8 znaków")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("Nazwa użytkownika: 3-50 znaków, tylko litery/cyfry/podkreślnik")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str

    model_config = {"from_attributes": True}  # pozwala tworzyć z SQLAlchemy 