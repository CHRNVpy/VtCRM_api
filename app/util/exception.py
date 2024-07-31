from fastapi import HTTPException

from app.schema.auth_schema import ErrorDetails


class VtCRM_HTTPException(HTTPException):
    def __init__(self, status_code: int, error_details: ErrorDetails):
        self.status_code = status_code
        self.error_details = error_details
