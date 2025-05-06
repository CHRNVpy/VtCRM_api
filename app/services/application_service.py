import asyncio
import datetime
import random

from fastapi import status

from app.crud.admin_crud import is_admin, get_version, update_version, get_user_id
from app.crud.application_crud import create_application, create_pool, get_application, \
    get_applications, update_app, get_pool_installer, all_pool_apps_finished, set_pool_status, \
    update_pool_status, get_pool, get_pools, get_installer_applications, add_step, add_step_image, add_step_equipment, \
    apps_hash_exists, get_application_id_by_hash, delete_steps, update_app_status_and_installer, all_pool_apps_approved, \
    update_pool_installer, get_installer_application
from app.crud.equipment_crud import update_equipment, reset_application_equipment, reset_installer_equipment, \
    set_equipment_installer
from app.crud.images_crud import update_image, reset_images
from app.crud.installer_crud import get_all_installers_data, get_user, get_free_installers_data
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
            await set_pool_status(app_id, 'finished')

    async def approve_pool(self, app_id: int):
        if await all_pool_apps_approved(app_id):
            await set_pool_status(app_id, 'approved')

    async def create_app(self, new_app: NewApplication, current_user: str) -> Application:

        if not await is_admin(current_user):
            raise VtCRM_HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                      error_details=ErrorDetails(code="You're not an admin"))
        # if new_app.ver != await get_version('applications'):
        #     raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                               error_details=ErrorDetails(code="Version mismatch"))

        try:
            if await apps_hash_exists(new_app.hash):
                application_id = await get_application_id_by_hash(new_app.hash)
                await update_app(new_app, application_id)
                await update_version('applications')
                if new_app.equipments:
                    await reset_application_equipment(application_id)
                    await asyncio.gather(*[update_equipment({"applicationId": application_id}, eq)
                                           for eq in new_app.equipments])
                app = await get_application(application_id)

                return Application(appVer=await get_version('applications'),
                                   imageVer=await get_version('images'), entity=app)
            else:
                if not new_app.poolId:
                    # installer = new_app.installerId
                    # if new_app.status == 'active':
                    #     installer = new_app.installerId
                    pool_id = await create_pool()
                    if new_app.status == 'active':
                        await  update_pool_status('active', pool_id)
                    new_app.poolId = pool_id

                # installer_id = await get_pool_installer(new_app.poolId)
                created_app_id = await create_application(new_app)
                await update_version('applications')
                if new_app.equipments:
                    await asyncio.gather(*[update_equipment({"applicationId": created_app_id}, eq)
                                           for eq in new_app.equipments])
                app = await get_application(created_app_id)

                return Application(appVer=await get_version('applications'),
                                   imageVer=await get_version('images'), entity=app)
        except Exception as e:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code=str(e)))

    async def list_apps(self, page: int, limit: int, pool_id: int, filter):
        applications = await get_applications(pool_id, filter)

        total_items = len(applications)
        paginated_items = self.paginate(applications, page, limit)
        total_pages = (total_items + limit - 1) // limit
        return ApplicationsList(appVer=await get_version('applications'),
                                             # imageVer=await get_version('images'),
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
                                # imageVer=await get_version('images'),
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
        if application.type == 'line setup':
            return Application(appVer=await get_version('applications'),
                               # imageVer=await get_version('images'),
                               entity=application)
        else:
            return Application(appVer=await get_version('applications'),
                               # imageVer=await get_version('images'),
                               entity=await get_application(app_id))

    async def update_app(self, updated_app: UpdatedApplicationData, application_id: int):
        # if updated_app.ver != await get_version('applications'):
        #     raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                               error_details=ErrorDetails(code="Version mismatch"))
        application = await get_application(application_id)
        if not application:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(
                                          code=f"Application doesn't exist with ID {updated_app.id}"))

        if application.status == 'active':
            updated_app.status = application.status

        await update_app(updated_app, application_id)
        await update_version('applications')
        if updated_app.equipments is not None:  # Check if equipments field is explicitly set
            if not updated_app.equipments:
                await reset_application_equipment(application_id)
            else:
                await reset_application_equipment(application_id)
                await asyncio.gather(*[update_equipment({"applicationId": application_id}, eq)
                                       for eq in updated_app.equipments])

        updated_application = await get_application(application_id)
        if updated_application.status == 'finished':
            await self.finish_pool(application_id)
        if updated_application.status == 'approved':
            await self.approve_pool(application_id)

        return Application(appVer=await get_version('applications'),
                           # imageVer=await get_version('images'),
                           entity=updated_application)

    async def get_installer_app(self, application_id: int):
        application = await get_application(application_id, steps=True)
        if not application:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code=f"Application doesn't exist "
                                                                      f"with ID {application_id}"))
        return Application(appVer=await get_version('applications'),
                           entity=application)

    async def update_installer_app(self,
                                   updated_app: UpdatedInstallerApplicationData,
                                   current_user: str,
                                   application_id: int):
        # if updated_app.ver != await get_version('applications'):
        #     raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                               error_details=ErrorDetails(code="Version mismatch"))

        application = await get_application(application_id)
        if not application:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(
                                          code=f"Application doesn't exist with ID {updated_app.id}"))

        installer_id = await get_user_id(current_user)

        await update_app(updated_app, application_id)

        if updated_app.images is not None:
            if updated_app.images:
                await asyncio.gather(*[
                    update_image(image_id, application_id, installer_id)
                    for image_id in updated_app.images
                ])
            else:
                await reset_images(application_id)

        await update_version('applications')
        if updated_app.status in ['finished', 'cancelled']:
            if updated_app.status == 'finished':
                await reset_installer_equipment(application_id)
            await self.finish_pool(application_id)
        # if updated_app.status == 'approved':
        #     await self.approve_pool(application_id)

        if updated_app.steps:
            await delete_steps(application_id)
            for step in updated_app.steps:

                step_id = await add_step(step, application_id)

                image_tasks = [add_step_image(step_id,
                                              application_id,
                                              installer_id,
                                              image_id) for image_id in step.images]

                update_image_ver_tasks = [update_version('images') for _ in range(len(image_tasks))]

                equipment_tasks = [add_step_equipment(step_id,
                                                      application_id,
                                                      equipment_id) for equipment_id in step.equipments]

                update_equipment_ver_tasks = [update_version('equipment') for _ in range(len(equipment_tasks))]

                await asyncio.gather(*image_tasks, *update_image_ver_tasks, *equipment_tasks, *update_equipment_ver_tasks)

                # return Application(appVer=await get_version('applications'),
                #                    # imageVer=await get_version('images'),
                #                    entity=await self.get_application(application_id, steps=True))

        return await self.get_app(application_id)

        # updated_application = await get_application(application_id, steps=True)
        #
        # return Application(appVer=await get_version('applications'),
        #                    # imageVer=await get_version('images'),
        #                    entity=updated_application)


    async def get_pools(self,
                        page: int,
                        limit: int,
                        installer_filter: str,
                        status_filter: str,
                        installed_date_filter: datetime.date) -> AppPools:
        total_items, pools = await get_pools(installer_filter,
                                             status_filter,
                                             installed_date_filter,
                                             page=page,
                                             page_size=limit)

        total_pages = (total_items + limit - 1) // limit
        return AppPools(appVer=await get_version('applications'),
                        entities=pools,
                        page=page,
                        perPage=limit,
                        pages=total_pages,
                        totalRows=total_items)

    async def get_pool(self, pool_id: int) -> AppPool:
        try:
            pool = await get_pool(pool_id)
        except Exception:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(
                                          code=f"Pool doesn't exist with ID {pool_id}"))
        return AppPool(appVer=await get_version('applications'),
                        entity=pool)

    async def update_pool(self, updated_pool: UpdatedPool, pool_id: int):
        # if updated_pool.ver != await get_version('applications'):
        #     raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                               error_details=ErrorDetails(code="Version mismatch"))
        try:
            current_pool = await get_pool(pool_id)
        except Exception:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(
                                          code=f"Pool doesn't exist with ID {updated_pool.id}"))
        if updated_pool.status == 'active':
            pool_installer_id = updated_pool.installerId
            # if not pool_installer_id:
            #     installers = [user.id for user in await get_free_installers_data()]
            #     pool_installer_id = random.choice(installers)
            update_app_status_tasks = [update_app_status_and_installer(app.id, 'active', pool_installer_id)
                                   for app in current_pool.entities if app.status != 'cancelled']
            await asyncio.gather(*update_app_status_tasks)
            await update_pool_installer(pool_id, pool_installer_id)

            await asyncio.gather(*[set_equipment_installer(app.id, pool_installer_id) for app in current_pool.entities])

        await update_pool_status(updated_pool.status, pool_id)
        await update_version('applications')
        updated_pool = await get_pool(pool_id)
        return AppPool(appVer=await get_version('applications'), entity=updated_pool)