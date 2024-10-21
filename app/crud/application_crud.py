import asyncio
import json
from typing import Optional, List, Union

import aiomysql

from app.core.config import configs
from app.crud.client_crud import get_client_data
from app.schema.application_schema import NewApplication, ApplicationData, UpdatedApplicationData, UpdatedPool, \
    AppPoolData, UpdatedInstallerApplicationData, LineSetupStep, LineSetupStepFull, LineSetupApplicationData, Coordinates
from app.schema.equipment_schema import Equipment
from app.schema.images_schema import CrmImage


async def apps_hash_exists(hash: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT hash FROM applications WHERE hash = %s', (hash,))
                result = await cur.fetchone()
                return result is not None


async def create_pool(installer_id: int | None) -> int:
    query = "INSERT INTO app_pool (status, installer_id) VALUES (%s, %s)"
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, ('pending', installer_id))
                await conn.commit()
                pool_id = cur.lastrowid
                return pool_id


async def get_pool_installer(pool_id: int):
    query = "SELECT installer_id FROM app_pool WHERE id = %s"
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, pool_id)
                result = await cur.fetchone()
                return result[0] if result else None

async def update_pool_installer(pool_id: int, installer_id: int):
    query = "UPDATE app_pool SET installer_id = %s WHERE id = %s"
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (installer_id, pool_id))
                await conn.commit()


async def create_application(new_app: NewApplication, installer_id: int) -> int:
    query = 'INSERT INTO applications ('
    columns = []
    values = []
    params = []

    columns.append("type")
    values.append("%s")
    params.append(new_app.type)
    columns.append("client")
    values.append("%s")
    params.append(new_app.client)
    columns.append("address")
    values.append("%s")
    params.append(new_app.address)
    columns.append("installer_id")
    values.append("%s")
    params.append(installer_id)
    columns.append("install_date")
    values.append("%s")
    params.append(new_app.installDate)
    if new_app.comment:
        columns.append("comment")
        values.append("%s")
        params.append(new_app.comment)
    columns.append("status")
    values.append("%s")
    params.append(new_app.status)
    columns.append("app_pool_id")
    values.append("%s")
    params.append(new_app.poolId)
    columns.append("hash")
    values.append("%s")
    params.append(new_app.hash)

    query += ", ".join(columns) + ") VALUES (" + ", ".join(values) + ")"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
                app_id = cur.lastrowid
                return app_id

async def get_application_id_by_hash(hash: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT id FROM applications WHERE hash = %s', (hash,))
                result = await cur.fetchone()
                return result[0] if result else None


async def get_application(app_id: int, steps: bool = False):
    base_query = '''SELECT 
                    a.*,
                    u.*,
                    ROW_NUMBER() OVER (ORDER BY ap.id) AS pool_row_id,
                    GROUP_CONCAT(
                        CONCAT(
                            '{"id":', i.id, 
                            ',"name":"', IFNULL(i.name, ''), 
                            '","mime_type":"', IFNULL(i.mime_type, ''), 
                            '","width":', IFNULL(i.width, 'null'), 
                            ',"height":', IFNULL(i.height, 'null'), 
                            ',"size":', IFNULL(i.size, 'null'), 
                            ',"path":"', IFNULL(i.path, ''), 
                            '","application_id":', IFNULL(i.application_id, 'null'), 
                            ',"installer_id":', IFNULL(i.installer_id, 'null'), 
                            '}'
                        )
                    ) AS images,
                    GROUP_CONCAT(
                        CONCAT(
                            '{"id":', e.id, 
                            ',"name":"', IFNULL(e.name, ''), 
                            '","serial":"', IFNULL(e.serial, ''), 
                            '","comment":"', IFNULL(e.comment, ''), 
                            '","hash":"', IFNULL(REPLACE(e.hash, '"', '\"'), ''), 
                            '"}'
                        )
                    ) AS equipment
                FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (ORDER BY id) AS row_num
                        FROM applications
                    ) AS a
                LEFT JOIN 
                    images i ON a.id = i.application_id
                LEFT JOIN
                    equipment e on a.id = e.application_id
                LEFT JOIN
                    users u ON a.installer_id = u.id
                LEFT JOIN
                    app_pool ap ON a.app_pool_id = ap.id
                WHERE a.id = %s
                GROUP BY a.id'''

    steps_query = '''SELECT
                    a.*,
                    u.*,
                    ROW_NUMBER() OVER (ORDER BY ap.id) AS pool_row_id,
                    IFNULL(JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'type', c.type,
                            'images', (
                                SELECT IFNULL(JSON_ARRAYAGG(
                                    JSON_OBJECT(
                                        'id', img.id,
                                        'name', img.name,
                                        'mimeType', img.mime_type,
                                        'width', img.width,
                                        'height', img.height,
                                        'size', img.size,
                                        'path', img.path,
                                        'applicationId', img.application_id,
                                        'installerId', img.installer_id
                                    )
                                ), JSON_ARRAY())
                                FROM images img
                                WHERE img.application_id = a.id AND img.step_id = c.id
                            ),
                            'coords', JSON_OBJECT(
                                'latitude', c.latitude,
                                'longitude', c.longitude
                            ),
                            'equipments', (
                                SELECT IFNULL(JSON_ARRAYAGG(
                                    JSON_OBJECT(
                                        'id', eq.id,
                                        'name', eq.name,
                                        'serialNumber', eq.serial,
                                        'status', eq.status,
                                        'comment', eq.comment,
                                        'applicationId', eq.application_id,
                                        'installerId', eq.installer_id,
                                        'hash', eq.hash
                                    )
                                ), JSON_ARRAY())
                                FROM equipment eq
                                WHERE eq.application_id = a.id AND eq.step_id = c.id
                            )
                        )
                    ), JSON_ARRAY()) AS steps
                FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (ORDER BY id) AS row_num
                        FROM applications
                    ) AS a
                LEFT JOIN
                    coordinates c ON c.application_id = a.id
                LEFT JOIN
                    users u ON a.installer_id = u.id
                LEFT JOIN
                    app_pool ap ON a.app_pool_id = ap.id
                WHERE
                    a.id = %s'''

    query = steps_query if steps else base_query

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, app_id)
                results = await cur.fetchone()
                if not results.get('id'):
                    return None

                if steps:
                    steps_str = results.get('steps')
                    if steps_str:
                        steps_obj = json.loads(steps_str)
                        steps = []
                        for step in steps_obj:
                            type = step.get('type')
                            images = step.get('images')
                            coords = step.get('coords')
                            equipment = step.get('equipments')

                            crm_images = [CrmImage(**img) for img in images]
                            crm_equipment = [Equipment(**eq) for eq in equipment]
                            coordinates = Coordinates(**coords) if coords else Coordinates()
                            if coords.get('latitude'):
                                steps.append(LineSetupStepFull(type=type,
                                                               images=crm_images,
                                                               coords=coordinates,
                                                               equipments=crm_equipment))

                        application_data = LineSetupApplicationData(id=results['id'],
                                                                    rowNum=results['row_num'],
                                                                    type=results['type'],
                                                                    client=await get_client_data(results['client']),
                                                                    address=results['address'],
                                                                    installer={"id": results['installer_id'],
                                                                               "firstname": results['firstname'],
                                                                               "middlename": results['middlename'],
                                                                               "lastname": results['lastname']},
                                                                    comment=results['comment'],
                                                                    status=results['status'],
                                                                    installDate=results['install_date'],
                                                                    poolId=results['app_pool_id'],
                                                                    poolRowNum=results['pool_row_id'],
                                                                    hash=results['hash'],
                                                                    steps=steps)
                        return application_data


                else:
                    # Parse the images JSON string
                    images_str = results.get('images')
                    equipment_str = results.get('equipment')

                    equipment = []
                    crm_images = []
                    if images_str:
                        images_list = images_str.split('},{')

                        # Properly format each JSON object
                        images_list = [img.strip('{}') for img in images_list]
                        images_list = ['{' + img + '}' for img in images_list]

                        # Parse each JSON object
                        for img_str in images_list:
                            img = json.loads(img_str)
                            crm_image = CrmImage(
                                id=img['id'],
                                name=img['name'],
                                mimeType=img['mime_type'],
                                width=img['width'],
                                height=img['height'],
                                size=img['size'],
                                path=img['path'],
                                installerId=img['installer_id'],
                                applicationId=img['application_id']
                            )
                            crm_images.append(crm_image)

                    if equipment_str:
                        equipment_list = equipment_str.split('},{')
                        # Properly format each JSON object
                        equipment_list = [item.strip('{}') for item in equipment_list]
                        equipment_list = ['{' + item + '}' for item in equipment_list]
                        # Parse each JSON object
                        for equipment_el in equipment_list:
                            equipment_json = json.loads(equipment_el)
                            equipment_model = Equipment(
                                id=equipment_json['id'],
                                name=equipment_json['name'],
                                serialNumber=equipment_json['serial'],
                                comment=equipment_json['comment'],
                                hash=equipment_json['hash']
                                # installerId=img['installer_id'],
                                # applicationId=img['application_id']
                            )
                            equipment.append(equipment_model)

                    # Create ApplicationImageData object
                    application_data = ApplicationData(
                        id=results['id'],
                        rowNum=results['row_num'],
                        type=results['type'],
                        client=await get_client_data(results['client']),
                        address=results['address'],
                        installer={"id": results['installer_id'],
                                   "firstname": results['firstname'],
                                   "middlename": results['middlename'],
                                   "lastname": results['lastname']},
                        comment=results['comment'],
                        status=results['status'],
                        installDate=results['install_date'],
                        poolId=results['app_pool_id'],
                        poolRowNum=results['pool_row_id'],
                        hash=results['hash'],
                        images=crm_images,
                        equipments=equipment
                    )

                    return application_data


async def get_applications(pool_id: Optional[int] = None, filter = None) -> list[ApplicationData]:
    query = '''SELECT 
                    a.*,
                    u.*,
                    GROUP_CONCAT(
                        CONCAT(
                            '{"id":', i.id, 
                            ',"name":"', IFNULL(i.name, ''), 
                            '","mime_type":"', IFNULL(i.mime_type, ''), 
                            '","width":', IFNULL(i.width, 'null'), 
                            ',"height":', IFNULL(i.height, 'null'), 
                            ',"size":', IFNULL(i.size, 'null'), 
                            ',"path":"', IFNULL(i.path, ''), 
                            '","application_id":', IFNULL(i.application_id, 'null'), 
                            ',"installer_id":', IFNULL(i.installer_id, 'null'), 
                            '}'
                        )
                    ) AS images,
                    GROUP_CONCAT(
                        CONCAT(
                            '{"id":', e.id, 
                            ',"name":"', IFNULL(e.name, ''), 
                            '","serial":"', IFNULL(e.serial, ''), 
                            '","comment":"', IFNULL(e.comment, ''), 
                            '","hash":"', IFNULL(REPLACE(e.hash, '"', '\"'), ''), 
                            '"}'
                        )
                    ) AS equipment
                FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (ORDER BY id) AS row_num
                        FROM applications
                    ) AS a
                LEFT JOIN 
                    images i ON a.id = i.application_id
                LEFT JOIN 
                    equipment e ON a.id = e.application_id
                LEFT JOIN
                    users u ON a.installer_id = u.id'''
    filters = []
    params = []

    # Add filters based on provided parameters
    if pool_id:
        filters.append("a.app_pool_id = %s")
        params.append(pool_id)

    if filter:
        filters.append('a.installer_id = %s OR a.client LIKE %s OR e.serial LIKE %s OR e.name LIKE %s '
                       'OR e.comment LIKE %s OR a.comment LIKE %s')
        params.extend([filter, f'%{filter}%', f'%{filter}%', f'%{filter}%', f'%{filter}%', f'%{filter}%'])


    # Combine filters into the query
    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " GROUP BY a.id"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params)
                results = await cur.fetchall()
                # return results
                processed_data = []
                for item in results:
                    # Parse the images JSON string
                    images_str = item.get('images')
                    equipment_str = item.get('equipment')

                    equipment = []
                    crm_images = []
                    if images_str:
                        images_list = images_str.split('},{')

                        # Properly format each JSON object
                        images_list = [img.strip('{}') for img in images_list]
                        images_list = ['{' + img + '}' for img in images_list]

                        # Parse each JSON object
                        for img_str in images_list:
                            img = json.loads(img_str)
                            crm_image = CrmImage(
                                id=img['id'],
                                name=img['name'],
                                mimeType=img['mime_type'],
                                width=img['width'],
                                height=img['height'],
                                size=img['size'],
                                path=img['path'],
                                installerId=img['installer_id'],
                                applicationId=img['application_id']
                            )
                            crm_images.append(crm_image)

                    if equipment_str:
                        equipment_list = equipment_str.split('},{')
                        # Properly format each JSON object
                        equipment_list = [item.strip('{}') for item in equipment_list]
                        equipment_list = ['{' + item + '}' for item in equipment_list]
                        # Parse each JSON object
                        for equipment_el in equipment_list:
                            equipment_json = json.loads(equipment_el)
                            equipment_model = Equipment(
                                id=equipment_json['id'],
                                name=equipment_json['name'],
                                serialNumber=equipment_json['serial'],
                                comment=equipment_json['comment'],
                                hash=equipment_json['hash'],
                                # rowNum=equipment_json['row_num']
                                # installerId=img['installer_id'],
                                # applicationId=img['application_id']
                            )
                            equipment.append(equipment_model)

                    # Create ApplicationImageData object
                    application_data = ApplicationData(
                        id=item['id'],
                        rowNum=item['row_num'],
                        type=item['type'],
                        client=await get_client_data(item['client']),
                        address=item['address'],
                        installer={"id": item['installer_id'],
                                   "firstname": item['firstname'],
                                   "middlename": item['middlename'],
                                   "lastname": item['lastname']},
                        comment=item['comment'],
                        status=item['status'],
                        installDate=item['install_date'],
                        poolId=item['app_pool_id'],
                        hash=item['hash'],
                        images=crm_images,
                        equipments=equipment
                    )
                    processed_data.append(application_data)
                return processed_data


async def get_installer_applications(current_user: str):
    query = '''SELECT 
                        a.*,
                        GROUP_CONCAT(
                            CONCAT(
                                '{"id":', i.id, 
                                ',"name":"', IFNULL(i.name, ''), 
                                '","mime_type":"', IFNULL(i.mime_type, ''), 
                                '","width":', IFNULL(i.width, 'null'), 
                                ',"height":', IFNULL(i.height, 'null'), 
                                ',"size":', IFNULL(i.size, 'null'), 
                                ',"path":"', IFNULL(i.path, ''), 
                                '","application_id":', IFNULL(i.application_id, 'null'), 
                                ',"installer_id":', IFNULL(i.installer_id, 'null'), 
                                '}'
                            )
                        ) AS images
                    FROM 
                        applications a
                    LEFT JOIN 
                        images i ON a.id = i.application_id 
                    WHERE a.installer_id = (SELECT id FROM users WHERE login = %s) GROUP BY a.id
                    ORDER BY a.install_date DESC'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, current_user)
                results = await cur.fetchall()
                processed_data = []
                for item in results:
                    # Parse the images JSON string
                    images_str = item.get('images')
                    crm_images = []
                    if images_str:
                        images_list = images_str.split('},{')

                        # Properly format each JSON object
                        images_list = [img.strip('{}') for img in images_list]
                        images_list = ['{' + img + '}' for img in images_list]

                        # Parse each JSON object
                        for img_str in images_list:
                            img = json.loads(img_str)
                            crm_image = CrmImage(
                                id=img['id'],
                                name=img['name'],
                                mimeType=img['mime_type'],
                                width=img['width'],
                                height=img['height'],
                                size=img['size'],
                                path=img['path'],
                                installerId=img['installer_id'],
                                applicationId=img['application_id']
                            )
                            crm_images.append(crm_image)

                    # Create ApplicationImageData object
                    application_data = ApplicationData(
                        id=item['id'],
                        type=item['type'],
                        client=await get_client_data(item['client']),
                        installerId=item['installer_id'],
                        comment=item['comment'],
                        status=item['status'],
                        installDate=item['install_date'],
                        poolId=item['app_pool_id'],
                        hash=item['hash'],
                        images=crm_images
                    )
                    processed_data.append(application_data)
                return processed_data


async def update_app(updated_app: UpdatedApplicationData):
    query = "UPDATE applications SET "

    updates = []
    params = []

    if updated_app.type:
        updates.append("type = %s")
        params.append(updated_app.type)
    if updated_app.client:
        updates.append("client = %s")
        params.append(updated_app.client)
    if updated_app.installerId:
        updates.append("installer_id = %s")
        params.append(updated_app.installerId)
    if updated_app.comment:
        updates.append("comment = %s")
        params.append(updated_app.comment)
    if updated_app.status:
        updates.append("status = %s")
        params.append(updated_app.status)
    if updated_app.installDate:
        updates.append("install_date = %s")
        params.append(updated_app.installDate)
    if updated_app.appPoolId:
        updates.append("app_pool_id = %s")
        params.append(updated_app.appPoolId)

    # Join updates with commas
    query += ", ".join(updates)

    # Add the WHERE clause to specify the entity to update
    query += " WHERE id = %s;"
    params.append(updated_app.id)

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()


async def update_app(updated_app: Union[NewApplication, UpdatedApplicationData, UpdatedInstallerApplicationData],
                     app_id: int):
    query = "UPDATE applications SET "

    updates = []
    params = []

    if isinstance(updated_app, Union[NewApplication, UpdatedApplicationData]) and updated_app.client:
        updates.append("client = %s")
        params.append(updated_app.client)
    if isinstance(updated_app, Union[NewApplication, UpdatedApplicationData]) and updated_app.comment:
        updates.append("comment = %s")
        params.append(updated_app.comment)
    if isinstance(updated_app, Union[NewApplication, UpdatedApplicationData]) and updated_app.address:
        updates.append("address = %s")
        params.append(updated_app.address)
    if updated_app.status:
        updates.append("status = %s")
        params.append(updated_app.status)
    if isinstance(updated_app, Union[NewApplication, UpdatedApplicationData]) and updated_app.installDate:
        updates.append("install_date = %s")
        params.append(updated_app.installDate)

    if updates:

        # Join updates with commas
        query += ", ".join(updates)

        # Add the WHERE clause to specify the entity to update
        query += " WHERE id = %s;"
        params.append(app_id)

        async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    await conn.commit()

async def update_app_status_and_installer(app_id: int, status: str, installer_id: int):
    query = 'UPDATE applications SET status = %s, installer_id = %s WHERE id = %s'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (status, installer_id, app_id))
                await conn.commit()

async def all_pool_apps_approved(app_id: int):
    query = '''SELECT status
                FROM applications
                WHERE status != 'cancelled' AND app_pool_id = (SELECT app_pool_id 
                FROM applications WHERE id = %s);'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, app_id)
                result = await cur.fetchall()
                all_approved = all(value == 'approved' for t in result for value in t)
                return all_approved


async def all_pool_apps_finished(app_id: int):
    query = '''SELECT status
                FROM applications
                WHERE status != 'cancelled' AND app_pool_id = (SELECT app_pool_id 
                FROM applications WHERE id = %s);'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, app_id)
                result = await cur.fetchall()
                all_finished = all(value == 'finished' for t in result for value in t)
                return all_finished


async def set_pool_status(app_id: int, status: str):
    query = '''UPDATE app_pool ap
                SET ap.status = %s 
                WHERE ap.id = (SELECT a.app_pool_id 
                FROM applications a WHERE a.id = %s);'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (status, app_id))
                await conn.commit()


async def update_pool_status(status, pool_id: int):
    query = '''UPDATE app_pool ap
                SET ap.status = %s 
                WHERE ap.id = %s;'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (status, pool_id))
                await conn.commit()


async def get_pool(pool_id: int) -> AppPoolData:
    query = '''
        SELECT 
            app_pool.id AS pool_id, 
            app_pool.status AS pool_status,
            app_pool.installer_id AS pool_installer,
            app_pool.row_num,
            users.firstname,
            users.middlename,
            users.lastname, 
            JSON_ARRAYAGG(
                JSON_OBJECT(
                    'id', applications.id, 
                    'type', applications.type,
                    'client', applications.client,
                    'installerId', applications.installer_id,
                    'comment', applications.comment,
                    'status', applications.status,
                    'address', applications.address,
                    'installDate', applications.install_date,
                    'hash', applications.hash,
                    'poolId', applications.app_pool_id,
                    'images', COALESCE((
                        SELECT JSON_ARRAYAGG(
                            JSON_OBJECT(
                                'id', images.id, 
                                'name', images.name, 
                                'mime_type', images.mime_type, 
                                'width', images.width, 
                                'height', images.height,
                                'size', images.size, 
                                'path', images.path,
                                'installerId', images.installer_id,
                                'applicationId', images.application_id
                            )
                        )
                        FROM images
                        WHERE images.application_id = applications.id
                    ), JSON_ARRAY())
                )
            ) AS applications
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (ORDER BY id) AS row_num
            FROM app_pool
        ) AS app_pool
        LEFT JOIN 
            applications ON app_pool.id = applications.app_pool_id
        LEFT JOIN 
            users ON app_pool.installer_id = users.id'''

    if pool_id:
        query += (" WHERE app_pool.id = %s "
                  "GROUP BY app_pool.id, app_pool.status")
    else:
        query += " GROUP BY app_pool.id, app_pool.status"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (pool_id,))
                app_pool = await cur.fetchone()
                pool_id, pool_status, pool_installer, pool_row_num, installer_name, installer_middlename, installer_lastname, applications_json = app_pool
                applications = json.loads(applications_json)
                applications_list = []
                for app in applications:
                    # Parse the images JSON string
                    images_list = app.get('images')
                    crm_images = []
                    if images_list:
                        # Parse each JSON object
                        for img in images_list:
                            crm_image = CrmImage(
                                id=img['id'],
                                name=img['name'],
                                mimeType=img['mime_type'],
                                width=img['width'],
                                height=img['height'],
                                size=img['size'],
                                path=img['path'],
                                installerId=img['installerId'],
                                applicationId=img['applicationId']
                            )
                            crm_images.append(crm_image)

                    # Create ApplicationImageData object
                    application_data = ApplicationData(
                        id=app['id'],
                        type=app['type'],
                        client=await get_client_data(app['client']),
                        installerId=app['installerId'],
                        comment=app['comment'],
                        status=app['status'],
                        address=app['address'],
                        installer={'id': pool_installer,
                                   'name': installer_name,
                                   'middlename': installer_middlename,
                                   'lastname': installer_lastname},
                        installDate=app['installDate'],
                        hash=app['hash'],
                        poolId=app['poolId'],
                        images=crm_images
                    )
                    applications_list.append(application_data)
                return AppPoolData(id=pool_id, poolRowNum=pool_row_num, status=pool_status, installerId=pool_installer,
                                   entities=applications_list) if app_pool else None


async def get_pools():
    query = '''
    SELECT 
    app_pool.id AS pool_id, 
    app_pool.status AS pool_status,
    app_pool.installer_id AS pool_installer,
    app_pool.row_num,
    users.firstname,
    users.middlename,
    users.lastname,
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', applications.id, 
            'type', applications.type,
            'client', applications.client,
            'installerId', applications.installer_id,
            'comment', applications.comment,
            'status', applications.status,
            'address', applications.address,
            'installDate', applications.install_date,
            'hash', applications.hash,
            'poolId', applications.app_pool_id,
            'images', COALESCE((
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'id', images.id, 
                        'name', images.name, 
                        'mime_type', images.mime_type, 
                        'width', images.width, 
                        'height', images.height,
                        'size', images.size, 
                        'path', images.path,
                        'installerId', images.installer_id,
                        'applicationId', images.application_id
                    )
                )
                FROM images
                WHERE images.application_id = applications.id
            ), JSON_ARRAY()),
            'equipment', COALESCE((
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'id', equipment.id, 
                        'name', equipment.name, 
                        'serial', equipment.serial, 
                        'comment', equipment.comment, 
                        'hash', equipment.hash
                    )
                )
                FROM equipment
                WHERE equipment.application_id = applications.id
            ), JSON_ARRAY())
        )
    ) AS applications
FROM (
        SELECT *,
               ROW_NUMBER() OVER (ORDER BY id) AS row_num
        FROM app_pool
    ) AS app_pool
LEFT JOIN 
    applications ON app_pool.id = applications.app_pool_id
LEFT JOIN 
    users ON app_pool.installer_id = users.id
GROUP BY 
    app_pool.id, app_pool.status;'''

    async with (aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool):
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                results = await cur.fetchall()
                processed_data = []
                for app_pool in results:
                    pool_id, pool_status, pool_installer, pool_row_num, installer_name, installer_middlename, installer_lastname, applications_json = app_pool
                    applications = json.loads(applications_json)
                    applications_list = []
                    for app in applications:
                        # Parse the images JSON string
                        images_list = app.get('images')
                        equipment_list = app.get('equipment')
                        crm_images = []
                        crm_equipment = []
                        if images_list:
                            # Parse each JSON object
                            for img in images_list:
                                crm_image = CrmImage(
                                    id=img['id'],
                                    name=img['name'],
                                    mimeType=img['mime_type'],
                                    width=img['width'],
                                    height=img['height'],
                                    size=img['size'],
                                    path=img['path'],
                                    installerId=img['installerId'],
                                    applicationId=img['applicationId']
                                )
                                crm_images.append(crm_image)

                        if equipment_list:
                            for item in equipment_list:
                                equipment_model = Equipment(
                                    id=item['id'],
                                    name=item['name'],
                                    serialNumber=item['serial'],
                                    comment=item['comment'],
                                    hash=item['hash']
                                )

                                crm_equipment.append(equipment_model)

                        # Create ApplicationImageData object
                        application_data = ApplicationData(
                            id=app['id'],
                            type=app['type'],
                            client=await get_client_data(app['client']),
                            installerId=app['installerId'],
                            comment=app['comment'],
                            status=app['status'],
                            address=app['address'],
                            installer={'id': pool_installer,
                                       'name': installer_name,
                                       'middlename': installer_middlename,
                                       'lastname': installer_lastname},
                            installDate=app['installDate'],
                            hash=app['hash'],
                            poolId=app['poolId'],
                            images=crm_images,
                            equipments=crm_equipment
                        )
                        applications_list.append(application_data)
                    processed_data.append(AppPoolData(id=pool_id, poolRowNum=pool_row_num, status=pool_status, installerId=pool_installer,
                                                      entities=applications_list))
                return processed_data

async def add_step(step: LineSetupStep, app_id: int):
    query = '''INSERT INTO coordinates (type, latitude, longitude, application_id) VALUES (%s, %s, %s, %s)'''
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (step.type, step.coords.latitude, step.coords.longitude, app_id))
                await conn.commit()
                return cur.lastrowid

async def add_step_image(step_id: int, image_id: int):
    query = '''UPDATE images SET step_id = %s WHERE id = %s'''
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (step_id, image_id))
                await conn.commit()


async def add_step_equipment(step_id: int, equipment_id: int):
    query = '''UPDATE equipment SET step_id = %s WHERE id = %s'''
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (step_id, equipment_id))
                await conn.commit()


async def delete_steps(application_id: int):
    update_equipment_query = '''UPDATE equipment SET step_id = NULL WHERE step_id IN 
                      (SELECT id FROM coordinates WHERE application_id = %s)'''
    update_images_query = '''UPDATE images SET step_id = NULL WHERE step_id IN 
                          (SELECT id FROM coordinates WHERE application_id = %s)'''
    delete_query = '''DELETE FROM coordinates WHERE application_id = %s'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(update_equipment_query, (application_id,))
                await cur.execute(update_images_query, (application_id,))
                await cur.execute(delete_query, (application_id,))
                await conn.commit()
