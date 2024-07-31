# from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.schema.application_schema import NewApplication, ApplicationResponse, ApplicationsResponse, \
    UpdatedApplicationData, UpdatedPool, AppPoolResponse
from app.services.application_service import AppService
from app.services.current_user_service import get_current_user

router = APIRouter(
    tags=["applications"],
)

service = AppService()


@router.get("/admin-application-collection",
            response_model=ApplicationsResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_applications(page: int = Query(1, ge=1), limit: int = Query(10, le=100),
                           pool_id: int = Query(None, description="Filters by pool"),
                           current_user: str = Depends(get_current_user)):
    total_pages, applications = await service.list_apps(page, limit, pool_id)
    return ApplicationsResponse(status='ok', data=applications, page=page, limit=limit, pages=total_pages)


@router.post("/admin-application",
             response_model=ApplicationResponse,
             responses={401: {"description": "Incorrect username or password"}})
async def create_application(new_app: NewApplication, current_user: str = Depends(get_current_user)):
    response = await service.create_app(new_app, current_user)
    return ApplicationResponse(status='ok', data=response)


@router.get("/admin-application",
            response_model=ApplicationResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_application(id: int = Query(None, description="Application id"),
                          current_user: str = Depends(get_current_user)):
    response = await service.get_app(id)
    return ApplicationResponse(status='ok', data=response)


@router.patch("/admin-application",
              response_model=ApplicationResponse,
              responses={401: {"description": "Incorrect username or password"}})
async def get_application(updated_app: UpdatedApplicationData,
                          current_user: str = Depends(get_current_user)):
    response = await service.update_app(updated_app)
    return ApplicationResponse(status='ok', data=response)


@router.patch("/admin-pool",
              response_model=AppPoolResponse,
              responses={401: {"description": "Incorrect username or password"}})
async def get_application(updated_pool: UpdatedPool,
                          current_user: str = Depends(get_current_user)):
    response = await service.update_pool(updated_pool)
    return AppPoolResponse(status='ok', data=response)
