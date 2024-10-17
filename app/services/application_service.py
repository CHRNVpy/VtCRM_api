import asyncio
import random

from fastapi import status

from app.crud.admin_crud import is_admin, get_version, update_version
from app.crud.application_crud import create_application, create_pool, get_application, \
    get_applications, update_app, get_pool_installer, all_pool_apps_finished, set_pool_status_finished, \
    update_pool_status, get_pool, get_pools, get_installer_applications, add_step, add_step_image, add_step_equipment, \
    apps_hash_exists, get_application_id_by_hash, delete_steps
from app.crud.installer_crud import get_all_installers_data
from app.schema.application_schema import NewApplication, Application, ApplicationsList, UpdatedApplicationData, \
    UpdatedPool, AppPool, AppPools, UpdatedInstallerApplicationData
from app.schema.error_schema import ErrorDetails
from app.util.exception import VtCRM_HTTPException


class AppService:

    def __init__(self):
        pass

    def paginate(self, data, page: int, limit: int):
        start = (page - 1) * limit
        end = start + limit
        return data[start:end]

    async def finish_pool(self, app_id: int):
        if await all_pool_apps_finished(app_id):
            await set_pool_status_finished(app_id)

    async def create_app(self, new_app: NewApplication, current_user: str) -> Application:
        if not await is_admin(current_user):
            raise VtCRM_HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                      error_details=ErrorDetails(code="You're not an admin"))
        if new_app.ver != await get_version('applications'):
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Version mismatch"))
        if await apps_hash_exists(new_app.hash):
            application_id = await get_application_id_by_hash(new_app.hash)
            await update_app(new_app, application_id)
            await update_version('applications')
            app = await get_application(application_id)
            return Application(appVer=await get_version('applications'),
                               imageVer=await get_version('images'), entity=app)
        else:
            if not new_app.poolId:
                installer = random.choice(await get_all_installers_data())
                pool_id = await create_pool(installer.id)
                new_app.poolId = pool_id

            installer_id = await get_pool_installer(new_app.poolId)
            created_app_id = await create_application(new_app, installer_id)
            await update_version('applications')
            app = await get_application(created_app_id)
            return Application(appVer=await get_version('applications'),
                               imageVer=await get_version('images'), entity=app)

    async def list_apps(self, page: int, limit: int, pool_id: int, filter):
        applications = await get_applications(pool_id, filter)

        total_items = len(applications)
        paginated_items = self.paginate(applications, page, limit)
        total_pages = (total_items + limit - 1) // limit
        return ApplicationsList(appVer=await get_version('applications'),
                                             imageVer=await get_version('images'),
                                             entities=paginated_items,
                                             page=page,
                                             perPage=limit,
                                             pages=total_pages,
                                             totalRows=total_items)

    async def list_installer_apps(self, current_user: str, page: int, limit: int):
        applications = await get_installer_applications(current_user)

        total_items = len(applications)
        paginated_items = self.paginate(applications, page, limit)
        total_pages = (total_items + limit - 1) // limit
        return ApplicationsList(appVer=await get_version('applications'),
                                imageVer=await get_version('images'),
                                entities=paginated_items,
                                page=page,
                                perPage=limit,
                                pages=total_pages,
                                totalRows=total_items)

    async def get_app(self, app_id: int):
        application = await get_application(app_id, steps=True)
        if not application:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code=f"Application doesn't exist with ID {app_id}"))

        return Application(appVer=await get_version('applications'),
                           imageVer=await get_version('images'),
                           entity=application)

    async def update_app(self, updated_app: UpdatedApplicationData, application_id: int):
        if updated_app.ver != await get_version('applications'):
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Version mismatch"))
        application = await get_application(application_id)
        if not application:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(
                                          code=f"Application doesn't exist with ID {updated_app.id}"))
        await update_app(updated_app, application_id)
        await update_version('applications')
        updated_application = await get_application(application_id)
        if updated_application.status == 'finished':
            await self.finish_pool(application_id)
        return Application(appVer=await get_version('applications'),
                           imageVer=await get_version('images'),
                           entity=updated_application)

    async def update_installer_app(self, updated_app: UpdatedInstallerApplicationData, application_id: int):
        if updated_app.ver != await get_version('applications'):
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Version mismatch"))

        application = await get_application(application_id)
        if not application:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(
                                          code=f"Application doesn't exist with ID {updated_app.id}"))

        await update_app(updated_app, application_id)
        await update_version('applications')
        if updated_app.status == 'finished':
            await self.finish_pool(application_id)

        if updated_app.steps:
            await delete_steps(application_id)
            for step in updated_app.steps:

                step_id = await add_step(step, application_id)

                image_tasks = [add_step_image(step_id, image_id) for image_id in step.images]
                update_image_ver_tasks = [update_version('images') for i in range(len(image_tasks))]
                equipment_tasks = [add_step_equipment(step_id, equipment_id) for equipment_id in step.equipments]
                update_equipment_ver_tasks = [update_version('equipment') for i in range(len(equipment_tasks))]

                await asyncio.gather(*image_tasks, *update_image_ver_tasks, *equipment_tasks, *update_equipment_ver_tasks)

                return Application(appVer=await get_version('applications'),
                                   imageVer=await get_version('images'),
                                   entity=await get_application(application_id, steps=True))

        updated_application = await get_application(updated_app.id)

        return Application(appVer=await get_version('applications'),
                           imageVer=await get_version('images'),
                           entity=updated_application)

    async def get_pools(self) -> AppPools:
        pools = await get_pools()
        return AppPools(appVer=await get_version('applications'), entities=pools)

    async def update_pool(self, updated_pool: UpdatedPool, pool_id: int):
        if updated_pool.appVer != await get_version('applications'):
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Version mismatch"))
        if not await get_pool(pool_id):
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(
                                          code=f"Pool doesn't exist with ID {updated_pool.id}"))
        await update_pool_status(updated_pool)
        await update_version('applications')
        updated_pool = await get_pool(pool_id)
        return AppPool(appVer=await get_version('applications'), entity=updated_pool)
