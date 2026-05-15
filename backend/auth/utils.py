import os
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict

import jwt
from jwt import PyJWTError

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

SECRET_KEY_DEFAULT = "photo-story-dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

users: Dict[str, dict] = {}

http_bearer = HTTPBearer()


def get_jwt_secret() -> str:
    return os.getenv("AUTH_SECRET_KEY", SECRET_KEY_DEFAULT)


def get_token_expire_delta() -> timedelta:
    return timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str) -> dict:
    user_id = str(uuid.uuid4())
    user_data = {
        "id": user_id,
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "usage_count": 0,
        "usage_limit": 5,
        "is_paid": False,
    }
    users[username] = user_data
    return user_data


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = users.get(username)
    if not user:
        return None
    if user["password_hash"] != hash_password(password):
        return None
    return user


def create_access_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + get_token_expire_delta(),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
    except PyJWTError:
        return None


def get_user(username: str) -> Optional[dict]:
    return users.get(username)


def increment_usage(username: str) -> int:
    user = users.get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["usage_count"] += 1
    return user["usage_count"]


def check_usage_limit(username: str) -> bool:
    user = users.get(username)
    if not user:
        return False
    return user["usage_count"] < user["usage_limit"] or user["is_paid"]


async def get_current_user(token: str = Depends(http_bearer)) -> dict:
    payload = decode_token(token.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    username = payload.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
