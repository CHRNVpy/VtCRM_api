from typing import Optional, Union, List, Literal

from fastapi import status

from pydantic import BaseModel, validator, field_validator

from app.schema.error_schema import ErrorDetails
from app.util.exception import VtCRM_HTTPException


class NewEquipment(BaseModel):
    ver: int
    name: str
    serialNumber: str
    comment: Optional[str] = None
    applicationId: Optional[int] = None
    installerId: Optional[int] = None
    hash: str

    @field_validator("name", "serialNumber", "hash", mode="before")
    def validate_non_empty(cls, value, field):
        if isinstance(value, str) and not value.strip():
            raise VtCRM_HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                      error_details=ErrorDetails(code=f"{field.field_name} cannot be empty or "
                                                                      f"only whitespace."))
        return value


class UpdatedEquipment(BaseModel):
    ver: int
    name: Optional[str] = None
    serialNumber: Optional[str] = None
    comment: Optional[str] = None
    applicationId: Optional[int] = None
    installerId: Optional[int] = None
    hash: str


class Equipment(BaseModel):
    id: int
    rowNum: Optional[int] = None
    name: str
    serialNumber: str
    comment: Optional[str] = None
    applicationId: Optional[int] = None
    installerId: Optional[int] = None
    hash: str


class SingleEquipment(BaseModel):
    ver: int
    entity: Equipment


class EquipmentList(BaseModel):
    ver: int
    entities: List[Equipment]
    page: int
    perPage: int
    pages: int
    totalRows: int


class EquipmentResponse(BaseModel):
    status: str
    data: Union[SingleEquipment, EquipmentList, ErrorDetails]


class PaginatedEquipmentResponse(BaseModel):
    status: str
    data: Union[EquipmentList, ErrorDetails]
    page: int
    limit: int
    pages: int
