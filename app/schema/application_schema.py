import datetime
from typing import Optional, Union, List, Literal

from pydantic import BaseModel

from app.schema.equipment_schema import Equipment
from app.schema.error_schema import ErrorDetails
from app.schema.images_schema import CrmImage


class ClientData(BaseModel):
    login: Optional[str] = None
    fullName: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None

class Coordinates(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class NewApplication(BaseModel):
    ver: int
    type: Optional[Literal['connection', 'repair', 'line setup']]
    client: Optional[str] = None
    address: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = 'pending'
    installDate: datetime.datetime
    poolId: Optional[int] = None
    hash: str


class UpdatedApplicationData(BaseModel):

    ver: int
    client: Optional[str] = None
    address: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled', 'approved']] = None
    installDate: Optional[datetime.datetime] = None

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
    status: Optional[Literal['finished']] = None
    installedDate: Optional[datetime.datetime] = None
    steps: Optional[List[LineSetupStep]] = None


class ApplicationData(BaseModel):
    id: int
    rowNum: Optional[int] = None
    type: Optional[Literal['connection', 'repair', 'line setup']] = None
    client: Optional[ClientData] = None
    address: Optional[str] = None
    installer: Optional[dict] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']] = None
    installDate: datetime.datetime
    poolId: Optional[int] = None
    hash: str
    images: Optional[List[CrmImage]] = []
    equipments: Optional[List[Equipment]] = []

class LineSetupApplicationData(BaseModel):
    id: int
    rowNum: int
    type: Optional[Literal['connection', 'repair', 'line setup']] = None
    client: Optional[ClientData] = None
    address: Optional[str] = None
    installer: Optional[dict] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']] = None
    installDate: datetime.datetime
    poolId: Optional[int] = None
    hash: str
    steps: Optional[List[LineSetupStepFull]] = []


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
