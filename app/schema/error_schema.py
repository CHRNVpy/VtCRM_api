from pydantic import BaseModel


class ErrorDetails(BaseModel):
    code: str
