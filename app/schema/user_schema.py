from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    login: str
    password: str
    role: Optional[str] = 'installer'
