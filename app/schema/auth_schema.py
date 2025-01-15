from typing import Union, Optional

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails
from app.schema.installer_schema import Installer
from app.schema.user_schema import User


class AuthTokens(BaseModel):
    accessToken: str
    refreshToken: str
    role: str


class RefreshToken(BaseModel):
    refreshToken: str


class Me(BaseModel):
    id: int
    login: str
    password: str
    firstname: Optional[str]
    middlename: Optional[str]
    lastname: Optional[str]
    phone: Optional[str]
    status: Optional[str]
    role: Optional[str]
    hash: Optional[str]


class AuthResponse(BaseModel):
    status: str
    data: Union[AuthTokens, Me, ErrorDetails]
