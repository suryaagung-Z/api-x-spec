"""Pydantic v2 schemas for auth endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Budi Santoso",
                "email": "budi@example.com",
                "password": "rahasia123",
            }
        }
    )

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Nama lengkap pengguna.",
        examples=["Budi Santoso"],
    )
    email: EmailStr = Field(
        description="Alamat email unik untuk akun ini.",
        examples=["budi@example.com"],
    )
    password: str = Field(
        min_length=8,
        max_length=72,
        description="Kata sandi minimal 8 karakter. Akan disimpan sebagai hash bcrypt.",
        examples=["rahasia123"],
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "budi@example.com",
                "password": "rahasia123",
            }
        }
    )

    email: EmailStr = Field(
        description="Alamat email yang terdaftar.",
        examples=["budi@example.com"],
    )
    password: str = Field(
        min_length=1,
        description="Kata sandi akun.",
        examples=["rahasia123"],
    )


class TokenResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkLTEyMyJ9.abc123",
                "token_type": "bearer",
            }
        }
    )

    access_token: str = Field(
        description="JWT Bearer token. Gunakan sebagai header `Authorization: Bearer <token>`.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkLTEyMyJ9.abc123"],
    )
    token_type: str = Field(
        default="bearer",
        description="Tipe token, selalu `bearer`.",
        examples=["bearer"],
    )


class UserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "Budi Santoso",
                "email": "budi@example.com",
                "role": "user",
                "created_at": "2026-01-15T08:00:00Z",
            }
        },
    )

    id: str = Field(
        description="UUID pengguna.",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    name: str = Field(
        description="Nama lengkap pengguna.",
        examples=["Budi Santoso"],
    )
    email: str = Field(
        description="Alamat email pengguna.",
        examples=["budi@example.com"],
    )
    role: str = Field(
        description="Peran pengguna: `user` atau `admin`.",
        examples=["user"],
    )
    created_at: datetime = Field(
        description="Waktu pembuatan akun (UTC).",
        examples=["2026-01-15T08:00:00Z"],
    )
