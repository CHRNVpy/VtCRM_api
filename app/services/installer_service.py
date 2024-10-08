import random

from app.crud.admin_crud import is_admin, add_installer
from app.crud.installer_crud import get_installer_data_by_hash, get_all_installers_data, hash_exists, \
    get_installer_data_by_id, update_installer
from app.crud.admin_crud import get_version, update_version
from app.schema.error_schema import ErrorDetails
from app.schema.installer_schema import NewInstaller, NewInstallerResponse, Installers, CurrentInstaller, \
    UpdateInstaller
from app.util.exception import VtCRM_HTTPException
from fastapi import status


class InstallerService:

    def __init__(self):
        pass

    def generate_login(self) -> str:
        return str(random.randint(10000, 99999))

    async def create_new_installer(self, new_installer: NewInstaller, current_user: str):
        if not await is_admin(current_user):
            raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      error_details=ErrorDetails(code="You're not an admin"))
        if new_installer.ver != await get_version('users'):
            raise VtCRM_HTTPException(status_code=status.HTTP_200_OK,
                                      error_details=ErrorDetails(code="Version mismatch"))
        if not await hash_exists(new_installer.hash):
            if not new_installer.login:
                new_installer.login = self.generate_login()
            try:
                await add_installer(new_installer)
                await update_version('users')
                installer = await get_installer_data_by_hash(new_installer.hash)
                return NewInstallerResponse(ver=await get_version('users'), entity=installer)
            except Exception as e:
                raise VtCRM_HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                          error_details=ErrorDetails(code=str(e)))
        else:
            installer = await get_installer_data_by_hash(new_installer.hash)
            await update_installer(new_installer, installer.id)
            await update_version('users')
            updated_installer = await get_installer_data_by_hash(new_installer.hash)
            return NewInstallerResponse(ver=await get_version('users'), entity=updated_installer)

    async def get_all_installers(self, current_user: str) -> Installers:
        if not await is_admin(current_user):
            raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      error_details=ErrorDetails(code="You're not an admin"))
        version = await get_version('users')
        installers = await get_all_installers_data()
        return Installers(ver=version, entities=installers)

    async def get_installer(self, current_user: str, installer_id: int):
        if not await is_admin(current_user):
            raise VtCRM_HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      error_details=ErrorDetails(code="You're not an admin"))
        installer = await get_installer_data_by_id(installer_id)
        if not installer:
            raise VtCRM_HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                      error_details=ErrorDetails(code="Installer ID not found"))
        return CurrentInstaller(ver=await get_version('users'), entity=installer)

    async def update_installer(self, updated_installer: UpdateInstaller, installer_id: int):
        if updated_installer.ver != await get_version('users'):
            raise VtCRM_HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                      error_details=ErrorDetails(code="Version mismatch"))
        installer = await get_installer_data_by_id(installer_id)
        if not installer:
            raise VtCRM_HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                      error_details=ErrorDetails(code="Installer ID not found"))
        await update_installer(updated_installer, installer_id)
        await update_version('users')
        updated_installer = await get_installer_data_by_id(installer_id)
        return CurrentInstaller(ver=await get_version('users'), entity=updated_installer)
