# from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request, Query

from app.schema.installer_schema import InstallerResponse, NewInstaller, InstallersResponse, UpdateInstaller
from app.services.current_user_service import get_current_user
from app.services.installer_service import InstallerService

router = APIRouter(
    tags=["installers"],
)

service = InstallerService()


@router.get("/installer-collection",
            response_model=InstallersResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_installers(current_user: str = Depends(get_current_user)):
    response = await service.get_all_installers(current_user)
    return InstallersResponse(status='ok', data=response)


@router.post("/installer",
             response_model=InstallerResponse,
             responses={401: {"description": "Incorrect username or password"}})
async def create_installer(installer: NewInstaller, current_user: str = Depends(get_current_user)):
    response = await service.create_new_installer(installer, current_user)
    return InstallerResponse(status='ok', data=response)


@router.get("/installer/{installer_id}",
            response_model=InstallerResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_installer(installer_id: int, current_user: str = Depends(get_current_user)):
    response = await service.get_installer(current_user, installer_id)
    return InstallerResponse(status='ok', data=response)


@router.patch("/installer/{installer_id}",
              # response_model=InstallerResponse,
              responses={401: {"description": "Incorrect username or password"}})
async def update_installer(updated_installer: UpdateInstaller,
                           installer_id: int,
                           current_user: str = Depends(get_current_user)):
    response = await service.update_installer(updated_installer, installer_id)
    return InstallerResponse(status='ok', data=response)
