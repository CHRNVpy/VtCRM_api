from typing import Optional, Literal

from pydantic import BaseModel


class User(BaseModel):
    login: str
    password: str
    role: Optional[Literal["admin", "installer"]] = "admin"
