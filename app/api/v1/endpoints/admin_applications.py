# from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.schema.application_schema import NewApplication, ApplicationResponse, PaginatedApplicationsResponse, \
    UpdatedApplicationData, UpdatedPool, AppPoolResponse, ApplicationsResponse
from app.services.application_service import AppService
from app.services.current_user_service import get_current_user

router = APIRouter(
    tags=["admin-applications"],
)

service = AppService()


@router.get("/admin-applications-collection",
            response_model=ApplicationsResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_applications(page: int = Query(1, ge=1), per_page: int = Query(10, le=100),
                           pool_id: int = Query(None, description="Filters by pool"),
                           filter: str = Query(None, description=""),
                           current_user: str = Depends(get_current_user)):
    applications = await service.list_apps(page, per_page, pool_id, filter)
    return ApplicationsResponse(status='ok', data=applications)


@router.post("/admin-application",
             response_model=ApplicationResponse,
             responses={401: {"description": "Incorrect username or password"}})
async def create_application(new_app: NewApplication, current_user: str = Depends(get_current_user)):
    response = await service.create_app(new_app, current_user)
    return ApplicationResponse(status='ok', data=response)


@router.get("/admin-application/{application_id}",
            response_model=ApplicationResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_application(application_id: int,
                          current_user: str = Depends(get_current_user)):
    response = await service.get_app(application_id)
    return ApplicationResponse(status='ok', data=response)


@router.patch("/admin-application/{application_id}",
              response_model=ApplicationResponse,
              responses={401: {"description": "Incorrect username or password"}})
async def update_application(updated_app: UpdatedApplicationData,
                             application_id: int,
                             current_user: str = Depends(get_current_user)):
    response = await service.update_app(updated_app, application_id)
    return ApplicationResponse(status='ok', data=response)


@router.get("/admin-pool-collection",
            response_model=AppPoolResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def update_pool(current_user: str = Depends(get_current_user)):
    response = await service.get_pools()
    return AppPoolResponse(status='ok', data=response)


# @router.patch("/admin-pool/{pool_id}",
#               response_model=AppPoolResponse,
#               responses={401: {"description": "Incorrect username or password"}})
# async def update_pool(updated_pool: UpdatedPool,
#                       pool_id: int,
#                       current_user: str = Depends(get_current_user)):
#     response = await service.update_pool(updated_pool, pool_id)
#     return AppPoolResponse(status='ok', data=response)
