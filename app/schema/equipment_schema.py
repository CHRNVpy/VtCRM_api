from typing import Optional, Union, List, Literal

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails


class NewEquipment(BaseModel):
    ver: int
    name: str
    serialNumber: str
    comment: Optional[str] = None
    applicationId: Optional[int] = None
    installerId: Optional[int] = None
    hash: str


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
    rowNum: int
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
