from typing import Optional, Union, List, Literal

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails


class NewInstaller(BaseModel):
    login: Optional[str] = None
    password: Optional[str] = None
    firstname: str
    middlename: str
    lastname: str
    phone: str
    status: Optional[Literal['active', 'inactive']] = 'active'
    role: str = 'installer'
    ver: int
    hash: str

class UpdateInstaller(BaseModel):

    ver: int
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    hash: str


class Installer(BaseModel):
    id: int
    login: str
    password: str
    firstname: str
    middlename: str
    lastname: str
    phone: str
    status: str
    role: str
    hash: str


class CurrentInstaller(BaseModel):
    ver: int
    entity: Installer


class NewInstallerResponse(BaseModel):
    ver: int
    entity: Installer


class Installers(BaseModel):
    ver: int
    entities: List[Installer]


class InstallersResponse(BaseModel):
    status: str
    data: Union[Installers, ErrorDetails]


class InstallerResponse(BaseModel):
    status: str
    data: Union[CurrentInstaller, ErrorDetails, NewInstallerResponse]
