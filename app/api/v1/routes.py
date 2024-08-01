from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.installers import router as installers_router
from app.api.v1.endpoints.equipment import router as equipment_router
from app.api.v1.endpoints.images import router as images_router
from app.api.v1.endpoints.admin_applications import router as admin_applications_router
from app.api.v1.endpoints.installer_applications import router as installer_applications_router

routers = APIRouter()
router_list = [auth_router, installers_router, equipment_router, images_router,
               admin_applications_router, installer_applications_router]

for router in router_list:
    router.tags = routers.tags.append("v1")
    routers.include_router(router)
