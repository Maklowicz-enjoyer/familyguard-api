
from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
import re
import uuid
from datetime import datetime

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

class DeviceRegisterRequest(BaseModel):
    device_name: str | None = None
    platform: str = "android"
    fcm_token: str | None = None

class DeviceResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_name: str | None
    platform: str
    registered_at: datetime
    model_config = {"from_attributes": True}

class GeneratePairingCodeRequest(BaseModel):
    device_id: uuid.UUID

class PairingCodeResponse(BaseModel):
    code: str
    expires_at: datetime
    model_config = {"from_attributes": True}

class ConfirmPairingRequest(BaseModel):
    code: str
    guardian_device_id: uuid.UUID

class DevicePairResponse(BaseModel):
    id: uuid.UUID
    child_device_id: uuid.UUID
    guardian_device_id: uuid.UUID
    paired_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}

class PairingStatusResponse(BaseModel):
    is_paired: bool
    pair_id: uuid.UUID | None = None
    paired_at: datetime | None = None


class LocationCreateRequest(BaseModel):
    device_id: uuid.UUID
    latitude: float
    longitude: float
    accuracy_meters: float | None = None
    battery_level: int | None = None

    @field_validator("latitude")
    @classmethod
    def latitude_range(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError("latitude musi być w zakresie -90..90")
        return v

    @field_validator("longitude")
    @classmethod
    def longitude_range(cls, v):
        if not (-180 <= v <= 180):
            raise ValueError("longitude musi być w zakresie -180..180")
        return v

    @field_validator("battery_level")
    @classmethod
    def battery_range(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("battery_level musi być w zakresie 0..100")
        return v


class LocationResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    latitude: float
    longitude: float
    accuracy_meters: float | None
    battery_level: int | None
    recorded_at: datetime
    model_config = {"from_attributes": True}