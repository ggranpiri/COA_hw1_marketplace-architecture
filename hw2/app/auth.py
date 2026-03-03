from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import bcrypt

from app.models import User
from app.errors import AppError
from app.security import create_access_token, create_refresh_token, decode_token

async def register(session: AsyncSession, email: str, password: str, role: str):
    exists = await session.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none():
        raise AppError("VALIDATION_ERROR", 400, "Validation failed", {"fields": [{"field": "email", "message": "already exists"}]})

    u = User(email=email, password_hash=bcrypt.hash(password), role=role)
    session.add(u)
    await session.flush()
    return u

async def login(session: AsyncSession, email: str, password: str):
    res = await session.execute(select(User).where(User.email == email))
    u = res.scalar_one_or_none()
    if not u or not bcrypt.verify(password, u.password_hash):
        raise AppError("TOKEN_INVALID", 401, "Invalid credentials")
    return {
        "access_token": create_access_token(u.id, u.role),
        "refresh_token": create_refresh_token(u.id, u.role),
    }

async def refresh(refresh_token: str):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise AppError("REFRESH_TOKEN_INVALID", 401, "Refresh token is invalid")
    return {"access_token": create_access_token(int(payload["sub"]), payload["role"])}