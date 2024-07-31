from datetime import datetime, timedelta

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import configs
from app.crud.admin_crud import is_admin
from app.crud.installer_crud import get_user_data
from app.crud.installer_crud import get_user, save_refresh_token, is_refresh_token_valid
from app.schema.auth_schema import RefreshToken, ErrorDetails
from app.schema.user_schema import User
from app.services.current_user_service import decode_token
from app.util.exception import VtCRM_HTTPException


class AuthService:
    def __init__(self):
        # self.user_repository = user_repository
        # super().__init__(user_repository)
        pass

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=configs.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, configs.SECRET_KEY, algorithm=configs.ALGORITHM)
        return encoded_jwt

    # Function to create refresh token
    def create_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=configs.REFRESH_TOKEN_EXPIRE_YEARS * 365)
        # expire = datetime.utcnow() + timedelta(minutes=1)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, configs.SECRET_KEY, algorithm=configs.ALGORITHM)
        return encoded_jwt

    def verify_password(self, plain_password, db_password):
        # return pwd_context.verify(plain_password, db_password)
        return plain_password == db_password

    async def authenticate_user(self, login: str, password: str):
        user = await get_user(login)
        if not user:
            return False
        if not self.verify_password(password, user.password):
            return False
        return user

    async def authorize(self, user: User):
        authenticated_user = await self.authenticate_user(user.login, user.password)
        if not authenticated_user:
            raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      error_details=ErrorDetails(code="Incorrect username or password"))
        access_token = self.create_access_token(data={"sub": user.login})
        refresh_token = self.create_refresh_token(data={"sub": user.login})

        await save_refresh_token(user.login, user.password, refresh_token)

        return {"accessToken": access_token, "refreshToken": refresh_token}

    async def refresh_access_token(self, request: RefreshToken):
        token_payload = decode_token(request.refreshToken)
        if not token_payload:
            raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      error_details=ErrorDetails(code="Invalid refresh token"))

        # Verify if the refresh token exists in the database
        is_valid = await is_refresh_token_valid(request.refreshToken)
        if not is_valid:
            raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      error_details=ErrorDetails(code="Invalid refresh token"))

        # Extract username from refresh token payload
        username = token_payload.get("sub")
        if not username:
            raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      error_details=ErrorDetails(code="Invalid refresh token"))

        # Generate a new access token
        access_token = self.create_access_token(data={"sub": username})

        return {"accessToken": access_token, "refreshToken": request.refreshToken}

    async def get_me(self, current_user):
        return await get_user_data(current_user)


