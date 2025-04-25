import datetime
from typing import Optional, Union, List, Literal

from pydantic import BaseModel, model_validator, field_validator

from app.schema.equipment_schema import Equipment
from app.schema.error_schema import ErrorDetails
from app.schema.images_schema import CrmImage


class ClientData(BaseModel):
    account: Optional[int | str] = None
    fullName: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None

class Coordinates(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class NewApplication(BaseModel):
    ver: int
    type: Optional[Literal['connection', 'repair']]
    client: Optional[int] = None
    address: Optional[str] = None
    problem: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = 'pending'
    installDate: datetime.date
    timeSlot: str
    # installerId: int
    poolId: Optional[int] = None
    equipments: Optional[List[int]] = None
    hash: str

    @field_validator('client', mode="before")
    def validate_client(cls, value):
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


class UpdatedApplicationData(BaseModel):
    ver: int
    client: Optional[int] = None
    address: Optional[str] = None
    problem: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = None
    installDate: Optional[datetime.date] = None
    timeSlot: Optional[str] = None
    # installerId: Optional[int] = None
    equipments: Optional[List[int]] = None


class LineSetupStep(BaseModel):
    type: Literal["start", "step", "stop"]
    images: List[int]
    coords: Coordinates
    equipments: List[int]

class LineSetupStepFull(BaseModel):
    type: Optional[Literal["start", "step", "stop"]] = None
    images: Optional[List[CrmImage]] = None
    coords: Optional[Coordinates] = None
    equipments: Optional[List[Equipment]] = None


class UpdatedInstallerApplicationData(BaseModel):

    ver: int
    status: Optional[Literal['finished', 'cancelled']] = None
    client: Optional[int | str] = None
    installedDate: Optional[datetime.date] = datetime.datetime.now().date()
    installerComment: Optional[str] = None
    images: Optional[List[int]] = None
    steps: Optional[List[LineSetupStep]] = None


class ApplicationData(BaseModel):
    id: Optional[int] = None
    rowNum: Optional[int] = None
    type: Optional[Literal['connection', 'repair', 'line setup']] = None
    client: Optional[ClientData] = None
    address: Optional[str] = None
    installer: Optional[dict] = None
    problem: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = None
    installDate: Optional[datetime.date] = None
    timeSlot: Optional[str] = None
    installedDate: Optional[datetime.date] = None
    installerComment: Optional[str] = None
    poolId: Optional[int] = None
    poolRowNum: Optional[int] = None
    hash: Optional[str] = None
    images: Optional[List[CrmImage]] = []
    equipments: Optional[List[Equipment]] = []

class LineSetupApplicationData(BaseModel):
    id: int
    rowNum: int
    type: Optional[Literal['connection', 'repair', 'line setup']] = None
    client: Optional[ClientData] = None
    address: Optional[str] = None
    installer: Optional[dict] = None
    problem: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = None
    installDate: datetime.date
    timeSlot: str
    installedDate: Optional[datetime.date] = None
    installerComment: Optional[str] = None
    poolId: Optional[int] = None
    poolRowNum: Optional[int] = None
    hash: str
    steps: Optional[List[LineSetupStepFull]] = []
    equipments: Optional[List[Equipment]] = []


class Application(BaseModel):
    appVer: int
    # imageVer: int
    entity: Union[ApplicationData, LineSetupApplicationData]


class ApplicationResponse(BaseModel):
    status: str
    data: Union[Application, ErrorDetails]


class ApplicationsList(BaseModel):
    appVer: int
    # imageVer: int
    entities: List[ApplicationData | LineSetupApplicationData]
    page: int
    perPage: int
    pages: int
    totalRows: int


class ApplicationsResponse(BaseModel):
    status: str
    data: Union[ApplicationsList, ErrorDetails]


class PaginatedApplicationsResponse(BaseModel):
    status: str
    data: Union[ApplicationsList, ErrorDetails]
    page: int
    limit: int
    pages: int


class AppPoolData(BaseModel):
    id: int
    poolRowNum: int
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = None
    installerId: Optional[int] = None
    entities: List[ApplicationData]


class UpdatedPool(BaseModel):
    ver: int
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']]
    installerId: Optional[int] = None

    @model_validator(mode='before')
    def check_installer_id(cls, values):
        if values.get("status") == "active" and values.get("installerId") is None:
            raise ValueError("installerId is required when status is 'active'")
        return values


class AppPool(BaseModel):
    appVer: int
    entity: AppPoolData


class AppPools(BaseModel):
    appVer: int
    entities: List[AppPoolData]
    page: int
    perPage: int
    pages: int
    totalRows: int


class AppPoolResponse(BaseModel):
    status: str
    data: Union[AppPool, AppPools, ErrorDetails]
