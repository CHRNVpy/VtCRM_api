from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.installers import router as installers_router
from app.api.v1.endpoints.equipment import router as equipment_router
from app.api.v1.endpoints.images import router as images_router
from app.api.v1.endpoints.applications import router as applications_router

routers = APIRouter()
router_list = [auth_router, installers_router, equipment_router, images_router, applications_router]

for router in router_list:
    router.tags = routers.tags.append("v1")
    routers.include_router(router)
