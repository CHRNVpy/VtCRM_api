from typing import Optional, Union, List

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails


class NewInstaller(BaseModel):
    login: Optional[str] = None
    password: str
    firstname: str
    middlename: str
    lastname: str
    phone: str
    status: Optional[str] = 'active'
    role: str = 'installer'
    ver: int
    hash: str


class Installer(BaseModel):
    id: int
    firstname: str
    middlename: str
    lastname: str
    phone: str
    status: str
    role: str


class UpdateInstaller(BaseModel):
    firstname: Optional[str] = ''
    middlename: Optional[str] = ''
    lastname: Optional[str] = ''
    phone: Optional[str] = ''
    status: Optional[str] = ''
    password: Optional[str] = ''


class CurrentInstaller(BaseModel):
    ver: int
    installer: Installer


class NewInstallerResponse(BaseModel):
    ver: int
    installer: Installer


class Installers(BaseModel):
    ver: int
    installers: List[Installer]


class InstallersResponse(BaseModel):
    status: str
    data: Union[Installers, ErrorDetails]


class InstallerResponse(BaseModel):
    status: str
    data: Union[CurrentInstaller, ErrorDetails, NewInstallerResponse]
