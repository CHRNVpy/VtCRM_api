from typing import Optional, Union, List

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails


class NewEquipment(BaseModel):
    ver: int
    name: str
    serialNumber: str
    comment: Optional[str] = None
    status: Optional[str] = None
    applicationId: Optional[int] = None
    installerId: Optional[int] = None


class UpdatedEquipment(BaseModel):
    ver: int
    name: Optional[str] = None
    serialNumber: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[str] = None
    applicationId: Optional[int] = None
    installerId: Optional[int] = None


class Equipment(BaseModel):
    id: int
    name: str
    serialNumber: str
    comment: Optional[str] = None
    status: Optional[str] = None
    applicationId: Optional[int] = None
    installerId: Optional[int] = None


class SingleEquipment(BaseModel):
    ver: int
    equipment: Equipment


class EquipmentList(BaseModel):
    ver: int
    equipment: List[Equipment]


class EquipmentResponse(BaseModel):
    status: str
    data: Union[SingleEquipment, ErrorDetails]


class PaginatedEquipmentResponse(BaseModel):
    status: str
    data: Union[EquipmentList, ErrorDetails]
    page: int
    limit: int
    pages: int
