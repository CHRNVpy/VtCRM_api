import datetime
from typing import Optional, Union, List, Literal

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails
from app.schema.images_schema import CrmImage


class NewApplication(BaseModel):
    ver: int
    type: str
    client: str
    comment: Optional[str] = None
    installDate: datetime.datetime
    poolId: Optional[int] = None


class UpdatedApplicationData(BaseModel):
    id: int
    type: Optional[str] = None
    client: Optional[str] = None
    installerId: Optional[int] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']] = None
    installDate: Optional[datetime.datetime] = None
    poolId: Optional[int] = None


class ApplicationData(BaseModel):
    id: int
    type: str
    client: str
    installerId: Optional[int] = None
    comment: Optional[str] = None
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']] = None
    installDate: datetime.datetime
    poolId: Optional[int] = None
    images: List[CrmImage]


class Application(BaseModel):
    appVer: int
    imageVer: int
    application: ApplicationData


class ApplicationResponse(BaseModel):
    status: str
    data: Union[Application, ErrorDetails]


class ApplicationsList(BaseModel):
    appVer: int
    imageVer: int
    applications: List[ApplicationData]


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
    applications: List[ApplicationData]


class UpdatedPool(BaseModel):
    appVer: int
    id: int
    status: Optional[Literal['active', 'pending', 'finished', 'cancelled']]


class AppPool(BaseModel):
    appVer: int
    pool: AppPoolData


class AppPools(BaseModel):
    appVer: int
    pools: List[AppPoolData]


class AppPoolResponse(BaseModel):
    status: str
    data: Union[AppPool, AppPools, ErrorDetails]
