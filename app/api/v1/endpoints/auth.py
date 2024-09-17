# from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

# from app.core.dependencies import get_current_active_user
from app.schema.auth_schema import AuthResponse, RefreshToken
from app.schema.user_schema import User
from app.services.auth_service import AuthService
from app.services.current_user_service import get_current_user

router = APIRouter(
    tags=["auth"],
)

service = AuthService()


@router.post("/auth",
             response_model=AuthResponse,
             responses={401: {"description": "Incorrect username or password"}})
async def get_access_token(user: User):
    result = await service.authorize(user)
    return AuthResponse(status='ok', data=result)


@router.post("/refresh-token",
             response_model=AuthResponse,
             responses={401: {"description": "Invalid refresh token"}})
async def refresh_token(request: RefreshToken):
    result = await service.refresh_access_token(request)
    return AuthResponse(status='ok', data=result)


@router.get('/me',
            response_model=AuthResponse,
            responses={401: {"description": "Invalid refresh token"}})
async def get_user(current_user: str = Depends(get_current_user)):
    result = await service.get_me(current_user)
    return AuthResponse(status='ok', data=result)
