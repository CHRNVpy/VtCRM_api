from typing import Optional, Union, List, Literal

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails


class NewInstaller(BaseModel):
    login: Optional[str] = None
    password: str
    firstname: str
    middlename: str
    lastname: str
    phone: str
    status: Optional[Literal['active', 'inactive']] = 'active'
    role: str = 'installer'
    ver: int
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


class UpdateInstaller(BaseModel):

    ver: int
    firstname: Optional[str] = ''
    middlename: Optional[str] = ''
    lastname: Optional[str] = ''
    phone: Optional[str] = ''
    status: Optional[str] = ''
    password: Optional[str] = ''
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
