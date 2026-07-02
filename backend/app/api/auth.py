"""认证 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, ChangePassword, TokenResponse, UserInfo
from app.services.auth_service import register_user, login_user, change_password
from app.dependencies import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register")
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    user = await register_user(db, data.username, data.password)
    return success(
        {"id": user.id, "username": user.username, "role": user.role},
        "注册成功",
    )


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录，返回 JWT Token"""
    result = await login_user(db, data.username, data.password)
    return success(result, "登录成功")


@router.put("/change-password")
async def change_pwd(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    await change_password(db, current_user, data.old_password, data.new_password)
    return success(message="密码修改成功")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return success(UserInfo.model_validate(current_user).model_dump())
