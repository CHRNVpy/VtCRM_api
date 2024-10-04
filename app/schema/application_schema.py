import datetime
from typing import Optional, Union, List, Literal

from pydantic import BaseModel

from app.schema.equipment_schema import Equipment
from app.schema.error_schema import ErrorDetails
from app.schema.images_schema import CrmImage


class ClientData(BaseModel):
    fullName: str
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None

class Coordinates(BaseModel):
    latitude: float
    longitude: float


class NewApplication(BaseModel):
    ver: int
    type: Optional[Literal['connection', 'repair', 'line setup']]
    client: str
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = 'pending'
    installDate: datetime.datetime
    poolId: Optional[int] = None


class UpdatedApplicationData(BaseModel):

    client: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = None
    installDate: Optional[datetime.datetime] = None

class LineSetupStep(BaseModel):
    type: Literal["start", "step", "stop"]
    images: List[int]
    coords: Coordinates
    equipments: List[int]

class LineSetupStepFull(BaseModel):
    type: Literal["start", "step", "stop"]
    images: List[CrmImage]
    coords: Coordinates
    equipments: List[Equipment]


class UpdatedInstallerApplicationData(BaseModel):

    ver: int
    status: Optional[Literal['finished']] = None
    installedDate: Optional[datetime.datetime] = None
    steps: Optional[List[LineSetupStep]] = None


class ApplicationData(BaseModel):
    id: int
    type: Optional[Literal['connection', 'repair', 'line setup']] = None
    client: Optional[ClientData] = None
    installerId: Optional[int] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']] = None
    installDate: datetime.datetime
    poolId: Optional[int] = None
    images: List[CrmImage]

class LineSetupApplicationData(BaseModel):
    id: int
    type: Optional[Literal['connection', 'repair', 'line setup']] = None
    client: ClientData
    installerId: Optional[int] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']] = None
    installDate: datetime.datetime
    poolId: Optional[int] = None
    steps: List[LineSetupStepFull]


class Application(BaseModel):
    appVer: int
    imageVer: int
    entity: Union[ApplicationData, LineSetupApplicationData]


class ApplicationResponse(BaseModel):
    status: str
    data: Union[Application, ErrorDetails]


class ApplicationsList(BaseModel):
    appVer: int
    imageVer: int
    entities: List[ApplicationData]
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
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']] = None
    installerId: int
    entities: List[ApplicationData]


class UpdatedPool(BaseModel):
    appVer: int
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']]


class AppPool(BaseModel):
    appVer: int
    entity: AppPoolData


class AppPools(BaseModel):
    appVer: int
    entities: List[AppPoolData]


class AppPoolResponse(BaseModel):
    status: str
    data: Union[AppPool, AppPools, ErrorDetails]
