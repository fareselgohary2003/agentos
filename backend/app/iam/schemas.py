import uuid

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255, pattern=r"^[a-z0-9-]+$")


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    organization_slug: str = Field(min_length=2, max_length=255, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: EmailStr
    full_name: str
    roles: list[str] = []

    model_config = {"from_attributes": True}
