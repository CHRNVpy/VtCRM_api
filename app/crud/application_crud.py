import asyncio
import datetime
import json
from pprint import pprint
from typing import Optional, List, Union

import aiomysql

from app.core.config import configs
from app.crud.client_crud import get_client_data, get_clients_data_batch
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


async def create_pool() -> int:
    query = "INSERT INTO app_pool (status) VALUES (%s)"
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, ('pending', ))
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


async def create_application(new_app: NewApplication) -> int:
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
    # columns.append("installer_id")
    # values.append("%s")
    # params.append(installer_id)
    columns.append("install_date")
    values.append("%s")
    params.append(new_app.installDate)
    columns.append("time_slot")
    values.append("%s")
    params.append(new_app.timeSlot)
    if new_app.problem:
        columns.append("problem")
        values.append("%s")
        params.append(new_app.problem)
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
                    ap_with_row.row_id AS pool_row_id,
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
                (SELECT ap.*, 
                        ROW_NUMBER() OVER (ORDER BY ap.id) AS row_id
                 FROM app_pool ap) ap_with_row ON a.app_pool_id = ap_with_row.id
                WHERE a.id = %s
                GROUP BY a.id'''

    steps_query = '''SELECT 
                    a.*,
                    ap_with_row.row_id AS pool_row_id,
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
                    ), JSON_ARRAY()) AS steps,
                    (SELECT JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'id', e.id,
                            'name', e.name,
                            'serialNumber', e.serial,
                            'status', e.status,
                            'comment', e.comment,
                            'applicationId', e.application_id,
                            'installerId', e.installer_id,
                            'hash', e.hash
                        )
                    ) FROM equipment e WHERE e.application_id = a.id) AS equipment,
                    u.*
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
                    (SELECT ap.*,
                     ROW_NUMBER() OVER (ORDER BY ap.id) AS row_id
                     FROM app_pool ap) ap_with_row ON a.app_pool_id = ap_with_row.id
                WHERE
                    a.id = %s
                GROUP BY a.id;'''

    query = steps_query if steps else base_query

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SET SESSION group_concat_max_len = 1000000")
                await cur.execute(query, app_id)
                results = await cur.fetchone()
                if not results:
                    return None

                if steps:
                    steps_str = results.get('steps')
                    equipment_str = results.get('equipment')
                    steps = []
                    equipment = []

                    if steps_str:

                        steps_obj = json.loads(steps_str)
                        for step in steps_obj:
                            step_type = step.get('type')
                            images = step.get('images')
                            coords = step.get('coords')
                            equipment = step.get('equipments')

                            crm_images = [CrmImage(**img) for img in images]
                            crm_equipment = [Equipment(**eq) for eq in equipment]
                            coordinates = Coordinates(**coords) if coords else Coordinates()
                            if coords.get('latitude'):
                                steps.append(LineSetupStepFull(type=step_type,
                                                               images=crm_images,
                                                               coords=coordinates,
                                                               equipments=crm_equipment))

                    if equipment_str:

                        equipment_list = json.loads(equipment_str)

                        # Parse each JSON object
                        for equipment_el in equipment_list:

                            equipment_model = Equipment(
                                id=equipment_el['id'],
                                name=equipment_el['name'],
                                serialNumber=equipment_el['serialNumber'],
                                comment=equipment_el['comment'],
                                hash=equipment_el['hash']
                                # installerId=img['installer_id'],
                                # applicationId=img['application_id']
                            )
                            equipment.append(equipment_model)

                    application_data = LineSetupApplicationData(id=results['id'],
                                                                rowNum=results['row_num'],
                                                                type=results['type'],
                                                                client=await get_client_data(results['client']),
                                                                address=results['address'],
                                                                installer={"id": results['installer_id'],
                                                                           "firstname": results['firstname'],
                                                                           "middlename": results['middlename'],
                                                                           "lastname": results['lastname']},
                                                                problem=results['problem'],
                                                                comment=results['comment'],
                                                                status=results['status'],
                                                                installDate=results['install_date'],
                                                                timeSlot=results['time_slot'],
                                                                installedDate=results['installed_date'],
                                                                installerComment=results['installer_comment'],
                                                                poolId=results['app_pool_id'],
                                                                poolRowNum=results['pool_row_id'],
                                                                hash=results['hash'],
                                                                steps=steps,
                                                                equipments=equipment)
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
                        problem=results['problem'],
                        comment=results['comment'],
                        status=results['status'],
                        installDate=results['install_date'],
                        timeSlot=results['time_slot'],
                        installedDate=results['installed_date'],
                        installerComment=results['installer_comment'],
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
                            '","applicationId":"', IFNULL(e.application_id, ''), 
                            '","installerId":"', IFNULL(e.installer_id, ''),  
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
                # print(results)
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
                                applicationId=equipment_json['applicationId'] if equipment_json['applicationId'] else None,
                                installerId=equipment_json['installerId'] if equipment_json['installerId'] else None

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
                        problem=item['problem'],
                        comment=item['comment'],
                        status=item['status'],
                        installDate=item['install_date'],
                        timeSlot=item['time_slot'],
                        installedDate=item['installed_date'],
                        installerComment=item['installer_comment'],
                        poolId=item['app_pool_id'],
                        hash=item['hash'],
                        images=crm_images,
                        equipments=equipment
                    )
                    processed_data.append(application_data)
                return processed_data


async def get_installer_applications(current_user: str):
    # Split the query: First fetch basic application data
    base_query = '''
        SELECT a.*, u.id as installer_id, u.firstname, u.middlename, u.lastname
        FROM applications a
        JOIN users u ON a.installer_id = u.id
        WHERE a.installer_id = (SELECT id FROM users WHERE login = %s) 
        AND a.status = 'active'
        ORDER BY a.install_date DESC
    '''

    # Initialize variables
    installer_applications = []

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            # Use a transaction to keep connection consistent across queries
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 1. Fetch base application data
                await cur.execute(base_query, current_user)
                applications = await cur.fetchall()

                if not applications:
                    return []

                # Build lookup dictionaries for related data
                app_ids = [app['id'] for app in applications]
                client_ids = [app['client'] for app in applications if app.get('client')]

                # 2. Batch fetch coordinates
                coords_query = '''
                    SELECT c.* 
                    FROM coordinates c
                    WHERE c.application_id IN ({})
                '''.format(','.join(['%s'] * len(app_ids)))
                await cur.execute(coords_query, app_ids)
                coordinates = await cur.fetchall()
                coords_by_app = {}
                for coord in coordinates:
                    app_id = coord['application_id']
                    if app_id not in coords_by_app:
                        coords_by_app[app_id] = []
                    coords_by_app[app_id].append(coord)

                # 3. Batch fetch images
                images_query = '''
                    SELECT img.*
                    FROM images img
                    WHERE img.application_id IN ({})
                '''.format(','.join(['%s'] * len(app_ids)))
                await cur.execute(images_query, app_ids)
                images = await cur.fetchall()
                images_by_app = {}
                images_by_step = {}
                for img in images:
                    app_id = img['application_id']
                    if app_id not in images_by_app:
                        images_by_app[app_id] = []
                    images_by_app[app_id].append(img)

                    if img.get('step_id'):
                        step_id = img['step_id']
                        if step_id not in images_by_step:
                            images_by_step[step_id] = []
                        images_by_step[step_id].append(img)

                # 4. Batch fetch equipment
                equipment_query = '''
                    SELECT eq.*
                    FROM equipment eq
                    WHERE eq.application_id IN ({})
                '''.format(','.join(['%s'] * len(app_ids)))
                await cur.execute(equipment_query, app_ids)
                equipment = await cur.fetchall()
                equipment_by_app = {}
                equipment_by_step = {}
                for eq in equipment:
                    app_id = eq['application_id']
                    if app_id not in equipment_by_app:
                        equipment_by_app[app_id] = []
                    equipment_by_app[app_id].append(eq)

                    if eq.get('step_id'):
                        step_id = eq['step_id']
                        if step_id not in equipment_by_step:
                            equipment_by_step[step_id] = []
                        equipment_by_step[step_id].append(eq)

    # 5. Batch fetch client data
    client_data_map = await get_clients_data_batch(client_ids)

    # 6. Process and build response objects with already fetched data
    for idx, item in enumerate(applications):
        app_id = item['id']
        row_num = idx + 1  # Calculate row_num sequentially

        # Process coordinates (steps) if they exist
        if app_id in coords_by_app and coords_by_app[app_id]:
            steps = []
            for coord in coords_by_app[app_id]:
                coord_id = coord['id']

                # Get images for this step
                step_images = []
                if coord_id in images_by_step:
                    step_images = [CrmImage(
                        id=img['id'],
                        name=img['name'],
                        mimeType=img['mime_type'],
                        width=img['width'],
                        height=img['height'],
                        size=img['size'],
                        path=img['path'],
                        applicationId=img['application_id'],
                        installerId=img.get('installer_id')
                    ) for img in images_by_step[coord_id]]

                # Get equipment for this step
                step_equipment = []
                if coord_id in equipment_by_step:
                    step_equipment = [Equipment(
                        id=eq['id'],
                        name=eq['name'],
                        serialNumber=eq['serial'],
                        status=eq.get('status'),
                        comment=eq.get('comment'),
                        applicationId=eq.get('application_id'),
                        installerId=eq.get('installer_id'),
                        hash=eq.get('hash')
                    ) for eq in equipment_by_step[coord_id]]

                # Create coordinates object
                coordinates = Coordinates(
                    latitude=coord.get('latitude'),
                    longitude=coord.get('longitude')
                ) if coord.get('latitude') else Coordinates()

                if coord.get('latitude'):
                    steps.append(LineSetupStepFull(
                        type=coord.get('type'),
                        images=step_images,
                        coords=coordinates,
                        equipments=step_equipment
                    ))

            application_data = LineSetupApplicationData(
                id=item['id'],
                rowNum=row_num,
                type=item.get('type'),
                client=client_data_map.get(item.get('client')),
                address=item.get('address'),
                installer={"id": item.get('installer_id'),
                           "firstname": item.get('firstname'),
                           "middlename": item.get('middlename'),
                           "lastname": item.get('lastname')},
                problem=item.get('problem'),
                comment=item.get('comment'),
                status=item.get('status'),
                installDate=item.get('install_date'),
                timeSlot=item.get('time_slot'),
                installedDate=item.get('installed_date'),
                installerComment=item.get('installer_comment'),
                poolId=item.get('app_pool_id'),
                hash=item.get('hash'),
                steps=steps
            )
        else:
            # Handle case with no coordinates (no steps)
            app_images = []
            if app_id in images_by_app:
                app_images = [CrmImage(
                    id=img['id'],
                    name=img['name'],
                    mimeType=img['mime_type'],
                    width=img['width'],
                    height=img['height'],
                    size=img['size'],
                    path=img['path'],
                    applicationId=img['application_id'],
                    installerId=img.get('installer_id')
                ) for img in images_by_app[app_id]]

            app_equipment = []
            if app_id in equipment_by_app:
                app_equipment = [Equipment(
                    id=eq['id'],
                    name=eq['name'],
                    serialNumber=eq['serial'],
                    status=eq.get('status'),
                    comment=eq.get('comment'),
                    applicationId=eq.get('application_id'),
                    installerId=eq.get('installer_id'),
                    hash=eq.get('hash')
                ) for eq in equipment_by_app[app_id]]

            application_data = ApplicationData(
                id=item['id'],
                rowNum=row_num,
                type=item.get('type'),
                client=client_data_map.get(item.get('client')),
                address=item.get('address'),
                installer={"id": item.get('installer_id'),
                           "firstname": item.get('firstname'),
                           "middlename": item.get('middlename'),
                           "lastname": item.get('lastname')},
                problem=item.get('problem'),
                comment=item.get('comment'),
                status=item.get('status'),
                installDate=item.get('install_date'),
                timeSlot=item.get('time_slot'),
                installedDate=item.get('installed_date'),
                installerComment=item.get('installer_comment'),
                poolId=item.get('app_pool_id'),
                hash=item.get('hash'),
                images=app_images,
                equipments=app_equipment
            )

        installer_applications.append(application_data)

    return installer_applications


async def get_installer_application(application_id: int):

    query = '''SELECT
                a.*,
                u.*,
                IFNULL(
                    CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM coordinates c
                            WHERE c.application_id = a.id
                        ) THEN JSON_ARRAYAGG(
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
                        )
                        ELSE JSON_ARRAY()
                    END,
                JSON_ARRAY()) AS steps,
                IFNULL((
                    SELECT JSON_ARRAYAGG(
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
                    )
                    FROM images img
                    WHERE img.application_id = a.id
                ), JSON_ARRAY()) AS images,
                IFNULL((
                    SELECT JSON_ARRAYAGG(
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
                    )
                    FROM equipment eq
                    WHERE eq.application_id = a.id
                ), JSON_ARRAY()) AS equipments
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (ORDER BY id) AS row_num
                FROM applications
            ) AS a
            LEFT JOIN
                coordinates c ON c.application_id = a.id
            LEFT JOIN
                users u ON a.installer_id = u.id
            WHERE a.id = %s;'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, application_id)
                item = await cur.fetchone()
                # pprint(item)

                steps_str = item.get('steps')
                steps_obj = json.loads(steps_str)
                if steps_obj:
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
                                                           equipments=crm_equipment
                                                       ))

                    application_data = LineSetupApplicationData(id=item['id'],
                                                                rowNum=item['row_num'],
                                                                type=item['type'],
                                                                client=await get_client_data(item['client']),
                                                                address=item['address'],
                                                                installer={"id": item['installer_id'],
                                                                           "firstname": item['firstname'],
                                                                           "middlename": item['middlename'],
                                                                           "lastname": item['lastname']},
                                                                problem=item['problem'],
                                                                comment=item['comment'],
                                                                status=item['status'],
                                                                installDate=item['install_date'],
                                                                timeSlot=item['time_slot'],
                                                                installedDate=item['installed_date'],
                                                                installerComment=item['installer_comment'],
                                                                poolId=item['app_pool_id'],
                                                                # poolRowNum=item['pool_row_id'],
                                                                hash=item['hash'],
                                                                steps=steps)

                else:

                    images_str = item.get('images')
                    equipment_str = item.get('equipments')

                    equipment = []
                    crm_images = []
                    if images_str:

                        images_obj = json.loads(images_str)

                        # Parse each JSON object
                        for img in images_obj:
                            crm_image = CrmImage(
                                id=img['id'],
                                name=img['name'],
                                mimeType=img['mimeType'],
                                width=img['width'],
                                height=img['height'],
                                size=img['size'],
                                path=img['path'],
                                installerId=img['installerId'],
                                applicationId=img['applicationId']
                            )
                            crm_images.append(crm_image)

                    if equipment_str:

                        equipment_obj = json.loads(equipment_str)
                        for equipment_el in equipment_obj:
                            equipment_model = Equipment(
                                id=equipment_el['id'],
                                name=equipment_el['name'],
                                serialNumber=equipment_el['serialNumber'],
                                comment=equipment_el['comment'],
                                hash=equipment_el['hash'],
                                # installerId=equipment_json['installer_id'],
                                # applicationId=equipment_json['application_id']
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
                        problem=item['problem'],
                        comment=item['comment'],
                        status=item['status'],
                        installDate=item['install_date'],
                        timeSlot=item['time_slot'],
                        installedDate=item['installed_date'],
                        installerComment=item['installer_comment'],
                        poolId=item['app_pool_id'],
                        # poolRowNum=results['pool_row_id'],
                        hash=item['hash'],
                        images=crm_images,
                        equipments=equipment
                    )

            return  application_data

# async def update_app(updated_app: UpdatedApplicationData):
#     query = "UPDATE applications SET "
#
#     updates = []
#     params = []
#
#     if updated_app.type:
#         updates.append("type = %s")
#         params.append(updated_app.type)
#     if updated_app.client:
#         updates.append("client = %s")
#         params.append(updated_app.client)
#     if updated_app.installerId:
#         updates.append("installer_id = %s")
#         params.append(updated_app.installerId)
#     if updated_app.problem:
#         updates.append("problem = %s")
#         params.append(updated_app.problem)
#     if updated_app.comment:
#         updates.append("comment = %s")
#         params.append(updated_app.comment)
#     if updated_app.status:
#         updates.append("status = %s")
#         params.append(updated_app.status)
#     if updated_app.installDate:
#         updates.append("install_date = %s")
#         params.append(updated_app.installDate)
#     if updated_app.appPoolId:
#         updates.append("app_pool_id = %s")
#         params.append(updated_app.appPoolId)
#
#     # Join updates with commas
#     query += ", ".join(updates)
#
#     # Add the WHERE clause to specify the entity to update
#     query += " WHERE id = %s;"
#     params.append(updated_app.id)
#
#     async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
#         async with pool.acquire() as conn:
#             async with conn.cursor() as cur:
#                 await cur.execute(query, params)
#                 await conn.commit()


async def update_app(updated_app: Union[NewApplication, UpdatedApplicationData, UpdatedInstallerApplicationData],
                     app_id: int):
    query = "UPDATE applications SET "

    updates = []
    params = []

    if (isinstance(updated_app, Union[NewApplication, UpdatedApplicationData, UpdatedInstallerApplicationData])
            and updated_app.client):
        updates.append("client = %s")
        params.append(updated_app.client)
    if isinstance(updated_app, Union[NewApplication, UpdatedApplicationData]) and updated_app.problem:
        updates.append("problem = %s")
        params.append(updated_app.problem)
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
    if isinstance(updated_app, Union[NewApplication, UpdatedApplicationData]) and updated_app.timeSlot:
        updates.append("time_slot = %s")
        params.append(updated_app.timeSlot)
    if isinstance(updated_app, UpdatedInstallerApplicationData) and updated_app.installedDate:
        updates.append("installed_date = %s")
        params.append(updated_app.installedDate)
    if isinstance(updated_app, UpdatedInstallerApplicationData) and updated_app.installerComment:
        updates.append("installer_comment = %s")
        params.append(updated_app.installerComment)
    if isinstance(updated_app, NewApplication) and updated_app.poolId:
        updates.append("app_pool_id = %s")
        params.append(updated_app.poolId)

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
                WHERE app_pool_id = (SELECT app_pool_id 
                FROM applications WHERE id = %s);'''

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, app_id)
                result = await cur.fetchall()
                all_finished = all(value in ('finished', 'cancelled') for t in result for value in t)
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
                    'problem', applications.problem,
                    'comment', applications.comment,
                    'status', applications.status,
                    'address', applications.address,
                    'installDate', applications.install_date,
                    'installedDate', applications.installed_date,
                    'installerComment', applications.installer_comment,
                    'timeSlot', applications.time_slot,
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
                            'installerId', equipment.installer_id,
                            'applicationId', equipment.application_id, 
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
                    equipment_list = app.get('equipment')
                    images_list = app.get('images')
                    crm_equipments = []
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

                    if equipment_list:
                        for item in equipment_list:
                            equipment_model = Equipment(
                                id=item['id'],
                                name=item['name'],
                                serialNumber=item['serial'],
                                comment=item['comment'],
                                applicationId=item['applicationId'],  # not sure we need this
                                installerId=item['installerId'],  # not sure we need this
                                hash=item['hash']
                            )

                            crm_equipments.append(equipment_model)

                    # Create ApplicationImageData object
                    application_data = ApplicationData(
                        id=app['id'],
                        type=app['type'],
                        client=await get_client_data(app['client']),
                        problem=app['problem'],
                        comment=app['comment'],
                        status=app['status'],
                        address=app['address'],
                        installer={'id': pool_installer,
                                   'firstname': installer_name,
                                   'middlename': installer_middlename,
                                   'lastname': installer_lastname},
                        installDate=app['installDate'],
                        installedDate=app['installedDate'],
                        installerComment=app['installerComment'],
                        timeSlot=app['timeSlot'],
                        hash=app['hash'],
                        poolId=app['poolId'],
                        images=crm_images,
                        equipments=crm_equipments
                    )
                    applications_list.append(application_data)
                return AppPoolData(id=pool_id, poolRowNum=pool_row_num, status=pool_status, installerId=pool_installer,
                                   entities=applications_list) if app_pool else None


async def get_pools(
        installer_name: str = None,
        status_filter: str = None,
        installed_date_filter: datetime.date = None,
        page: int = 1,
        page_size: int = 20
):
    """Get pools with pagination and optimized queries, returning total count."""
    offset = (page - 1) * page_size

    # Base conditions for the user/pool level filters
    pool_conditions = []
    pool_filters = []

    if installer_name:
        pool_conditions.append(
            '(LOWER(u.firstname) LIKE %s OR LOWER(u.lastname) LIKE %s OR LOWER(u.middlename) LIKE %s)'
        )
        pool_filters.extend([f'%{installer_name.lower()}%'] * 3)

    if status_filter:
        # Only get pools that have at least one application with this status
        pool_conditions.append('EXISTS (SELECT 1 FROM applications a WHERE a.app_pool_id = ap.id AND a.status = %s)')
        pool_filters.append(status_filter)

    if installed_date_filter:
        # Only get pools that have at least one application with this installed date
        pool_conditions.append(
            'EXISTS (SELECT 1 FROM applications a WHERE a.app_pool_id = ap.id AND DATE(a.installed_date) = %s)')
        pool_filters.append(installed_date_filter)

    where_clause = ' WHERE ' + ' AND '.join(pool_conditions) if pool_conditions else ''

    # Step 0: Count query to get total number of pools that match our filters
    count_query = f'''
    SELECT COUNT(*) as total_count
    FROM (
        SELECT *, ROW_NUMBER() OVER (ORDER BY id) AS row_num
        FROM app_pool
    ) AS ap
    LEFT JOIN users u ON ap.installer_id = u.id
    {where_clause}
    '''

    # Step 1: Get the basic pool data with pagination
    pool_query = f'''
    SELECT 
        ap.id AS pool_id, 
        ap.status AS pool_status,
        ap.installer_id AS pool_installer,
        ap.row_num,
        u.firstname,
        u.middlename,
        u.lastname
    FROM (
        SELECT *, ROW_NUMBER() OVER (ORDER BY id) AS row_num
        FROM app_pool
    ) AS ap
    LEFT JOIN users u ON ap.installer_id = u.id
    {where_clause}
    ORDER BY ap.id DESC LIMIT %s OFFSET %s;
    '''

    # Execute queries using connection pool
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            # Create cursor with dictionary=True to get results as dicts
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # Step 0: Get total count
                await cur.execute(count_query, pool_filters)
                count_result = await cur.fetchone()
                total_pools = count_result['total_count']

                # Add pagination parameters to filters
                data_filters = pool_filters.copy()
                data_filters.append(page_size)
                data_filters.append(offset)

                # Step 1: Get pools with pagination
                await cur.execute(pool_query, data_filters)
                pool_results = await cur.fetchall()

                if not pool_results:
                    return total_pools, []

                processed_pools = []

                # Get pool IDs for IN clause
                pool_ids = [pool['pool_id'] for pool in pool_results]
                placeholders = ', '.join(['%s'] * len(pool_ids))

                # Step 2: Get applications for these pools with applied filters
                app_query = f'''
                SELECT 
                    a.id, a.type, a.client, a.installer_id, a.comment, a.problem,
                    a.status, a.address, a.install_date, a.installed_date, a.installer_comment,
                    a.time_slot, a.hash, a.app_pool_id
                FROM applications a
                WHERE a.app_pool_id IN ({placeholders})
                '''

                app_filters = pool_ids.copy()

                # Apply the status filter to applications
                if status_filter:
                    app_query += " AND a.status = %s"
                    app_filters.append(status_filter)

                # Apply the installed date filter to applications
                if installed_date_filter:
                    app_query += " AND DATE(a.installed_date) = %s"
                    app_filters.append(installed_date_filter)

                await cur.execute(app_query, app_filters)
                app_results = await cur.fetchall()

                client_ids = [app['client'] for app in app_results if app.get('client')]
                client_data_map = await get_clients_data_batch(client_ids)

                # Group applications by pool_id
                apps_by_pool = {}
                all_app_ids = []

                for app in app_results:
                    pool_id = app['app_pool_id']
                    if pool_id not in apps_by_pool:
                        apps_by_pool[pool_id] = []

                    apps_by_pool[pool_id].append(app)
                    all_app_ids.append(app['id'])

                if not all_app_ids:
                    # Return pools with empty application lists if no apps found
                    for pool in pool_results:
                        processed_pools.append(
                            AppPoolData(
                                id=pool['pool_id'],
                                poolRowNum=pool['row_num'],
                                status=pool['pool_status'],
                                installerId=pool['pool_installer'],
                                entities=[]
                            )
                        )
                    return total_pools, processed_pools

                # Step 3: Get images for these applications
                app_placeholders = ', '.join(['%s'] * len(all_app_ids))
                images_query = f'''
                SELECT 
                    id, name, mime_type, width, height, size, path, 
                    installer_id, application_id
                FROM images
                WHERE application_id IN ({app_placeholders})
                '''

                await cur.execute(images_query, all_app_ids)
                images_results = await cur.fetchall()

                # Group images by application_id
                images_by_app = {}
                for img in images_results:
                    app_id = img['application_id']
                    if app_id not in images_by_app:
                        images_by_app[app_id] = []
                    images_by_app[app_id].append(img)

                # Step 4: Get equipment for these applications
                equipment_query = f'''
                SELECT 
                    id, name, serial, comment, installer_id, application_id, hash
                FROM equipment
                WHERE application_id IN ({app_placeholders})
                '''

                await cur.execute(equipment_query, all_app_ids)
                equipment_results = await cur.fetchall()

                # Group equipment by application_id
                equipment_by_app = {}
                for item in equipment_results:
                    app_id = item['application_id']
                    if app_id not in equipment_by_app:
                        equipment_by_app[app_id] = []
                    equipment_by_app[app_id].append(item)

                # Step 5: Process pools
                clients_cache = {}  # Cache for client data

                for pool in pool_results:
                    pool_id = pool['pool_id']
                    applications_list = []

                    for app in apps_by_pool.get(pool_id, []):
                        app_id = app['id']

                        # Process images for this application
                        crm_images = []
                        for img in images_by_app.get(app_id, []):
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

                        # Process equipment for this application
                        crm_equipment = []
                        for item in equipment_by_app.get(app_id, []):
                            equipment_model = Equipment(
                                id=item['id'],
                                name=item['name'],
                                serialNumber=item['serial'],
                                comment=item['comment'],
                                applicationId=item['application_id'],
                                installerId=item['installer_id'],
                                hash=item['hash']
                            )
                            crm_equipment.append(equipment_model)

                        # Get client data (cached)
                        client_id = app['client']
                        # if client_id not in clients_cache:
                        #     clients_cache[client_id] = await get_client_data(client_id)

                        # Create ApplicationData object
                        application_data = ApplicationData(
                            id=app_id,
                            type=app['type'],
                            client=client_data_map.get(client_id),
                            problem=app['problem'],
                            comment=app['comment'],
                            status=app['status'],
                            address=app['address'],
                            installer={
                                'id': pool['pool_installer'],
                                'firstname': pool['firstname'],
                                'middlename': pool['middlename'],
                                'lastname': pool['lastname']
                            },
                            installDate=app['install_date'],
                            installedDate=app['installed_date'],
                            installerComment=app['installer_comment'],
                            timeSlot=app['time_slot'],
                            hash=app['hash'],
                            poolId=app['app_pool_id'],
                            images=crm_images,
                            equipments=crm_equipment
                        )

                        applications_list.append(application_data)

                    # Create pool object
                    processed_pool = AppPoolData(
                        id=pool_id,
                        poolRowNum=pool['row_num'],
                        status=pool['pool_status'],
                        installerId=pool['pool_installer'],
                        entities=applications_list
                    )

                    processed_pools.append(processed_pool)

                return total_pools, processed_pools

async def add_step(step: LineSetupStep, app_id: int):
    query = '''INSERT INTO coordinates (type, latitude, longitude, application_id) VALUES (%s, %s, %s, %s)'''
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (step.type, step.coords.latitude, step.coords.longitude, app_id))
                await conn.commit()
                return cur.lastrowid

async def add_step_image(step_id: int, application_id: int, installer_id: int, image_id: int):
    query = '''UPDATE images SET application_id = %s, installer_id = %s, step_id = %s WHERE id = %s'''
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (application_id, installer_id, step_id, image_id))
                await conn.commit()


async def add_step_equipment(step_id: int,
                             application_id: int,
                             equipment_id: int):
    query = '''UPDATE equipment SET application_id = %s, installer_id = %s, step_id = %s WHERE id = %s'''
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (application_id, None, step_id, equipment_id))
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
