import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, Header
from app.errors import AppError

JWT_SECRET = os.environ["JWT_SECRET"]
ALGO = "HS256"

ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "20"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))

def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGO)

def create_refresh_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=REFRESH_TOKEN_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGO)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except JWTError:
        raise AppError("TOKEN_INVALID", 401, "Access token invalid")

def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("TOKEN_INVALID", 401, "Access token invalid")
    return authorization.removeprefix("Bearer ").strip()

def current_user(payload: dict = Depends(lambda token=Depends(get_bearer_token): decode_token(token))):
    if payload.get("type") != "access":
        raise AppError("TOKEN_INVALID", 401, "Access token invalid")
    return {"id": int(payload["sub"]), "role": payload["role"]}

def require_role(*roles: str):
    def dep(user=Depends(current_user)):
        if user["role"] not in roles:
            raise AppError("ACCESS_DENIED", 403, "Access denied")
        return user
    return dep