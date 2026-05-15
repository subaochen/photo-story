from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from .utils import create_user, authenticate_user, create_access_token, get_current_user, get_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


@router.post("/register")
async def register(request: RegisterRequest):
    if get_user(request.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    user = create_user(request.username, request.password)
    token = create_access_token(user["id"], user["username"])
    return {
        "user_id": user["id"],
        "username": user["username"],
        "token": token,
        "usage_limit": user["usage_limit"],
    }


@router.post("/login")
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user["id"], user["username"])
    return {
        "user_id": user["id"],
        "username": user["username"],
        "token": token,
        "usage_count": user["usage_count"],
        "usage_limit": user["usage_limit"],
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["id"],
        "username": current_user["username"],
        "usage_count": current_user["usage_count"],
        "usage_limit": current_user["usage_limit"],
        "is_paid": current_user["is_paid"],
    }
