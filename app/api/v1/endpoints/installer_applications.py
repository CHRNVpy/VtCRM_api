# from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.schema.application_schema import ApplicationResponse, ApplicationsResponse, UpdatedInstallerApplicationData
from app.services.application_service import AppService
from app.services.current_user_service import get_current_user

router = APIRouter(
    tags=["installer-applications"],
)

service = AppService()


@router.get("/installer-application-collection",
            response_model=ApplicationsResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_installer_applications(page: int = Query(1, ge=1), per_page: int = Query(10, le=100),
                                     current_user: str = Depends(get_current_user)):
    applications = await service.list_installer_apps(current_user, page, per_page)
    return ApplicationsResponse(status='ok', data=applications)


@router.get("/installer-application/{application_id}",
            response_model=ApplicationResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_installer_application(application_id: int,
                                    current_user: str = Depends(get_current_user)):
    response = await service.get_app(application_id)
    return ApplicationResponse(status='ok', data=response)


@router.patch("/installer-application/{application_id}",
              response_model=ApplicationResponse,
              responses={401: {"description": "Incorrect username or password"}})
async def update_installer_application(updated_app: UpdatedInstallerApplicationData,
                                       application_id: int,
                                       current_user: str = Depends(get_current_user)):
    response = await service.update_installer_app(updated_app, current_user, application_id)
    return ApplicationResponse(status='ok', data=response)
