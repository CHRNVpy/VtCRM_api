# from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.schema.application_schema import ApplicationResponse, ApplicationsResponse
from app.services.application_service import AppService
from app.services.current_user_service import get_current_user

router = APIRouter(
    tags=["installer-applications"],
)

service = AppService()


@router.get("/installer-application-collection",
            response_model=ApplicationsResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_installer_applications(current_user: str = Depends(get_current_user)):
    applications = await service.list_installer_apps(current_user)
    return ApplicationsResponse(status='ok', data=applications)


@router.get("/installer-application",
            response_model=ApplicationResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_installer_application(id: int = Query(None, description="Application id"),
                          current_user: str = Depends(get_current_user)):
    response = await service.get_app(id)
    return ApplicationResponse(status='ok', data=response)


# @router.patch("/installer-application",
#               response_model=ApplicationResponse,
#               responses={401: {"description": "Incorrect username or password"}})
# async def update_application(updated_app: UpdatedApplicationData,
#                              current_user: str = Depends(get_current_user)):
#     response = await service.update_app(updated_app)
#     return ApplicationResponse(status='ok', data=response)
