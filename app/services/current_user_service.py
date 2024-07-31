from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from app.core.config import configs
from app.schema.error_schema import ErrorDetails
from app.util.exception import VtCRM_HTTPException


def decode_token(token: str):
    try:
        payload = jwt.decode(token, configs.SECRET_KEY, algorithms=[configs.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token = credentials.credentials
    if not token:
        raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                  error_details=ErrorDetails(code="Invalid access token"))
    payload = decode_token(token)
    if payload is None:
        raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                  error_details=ErrorDetails(code="Invalid access token"))
    return payload.get("sub")
