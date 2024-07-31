from typing import Union

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails
from app.schema.installer_schema import Installer
from app.schema.user_schema import User


class AuthTokens(BaseModel):
    accessToken: str
    refreshToken: str


class RefreshToken(BaseModel):
    refreshToken: str


class AuthResponse(BaseModel):
    status: str
    data: Union[AuthTokens, User, Installer, ErrorDetails]
