import asyncio
from typing import Union

import aiomysql

from app.core.config import configs
from app.schema.equipment_schema import Equipment, NewEquipment, UpdatedEquipment


async def equipment_hash_exists(hash: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT hash FROM equipment WHERE hash = %s', (hash,))
                result = await cur.fetchone()
                return result is not None


async def get_all_equipment(name_filter: str = None,
                            status_filter: str = None,
                            installer_filter: int = None):
    query = '''SELECT * FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (ORDER BY id) AS row_num
                        FROM equipment
                    ) AS numbered_rows
                LEFT JOIN applications a ON numbered_rows.application_id = a.id
                WHERE 1=1
                '''
    filters = []

    if name_filter:
        query += ' AND (name LIKE %s OR serial LIKE %s OR comment LIKE %s)'
        filters.extend([f'%{name_filter}%', f'%{name_filter}%', f'%{name_filter}%'])

    if status_filter and status_filter == 'base':
        query += ' AND numbered_rows.installer_id IS NULL AND numbered_rows.application_id IS NULL'

    if status_filter and status_filter == 'installer':
        query += ' AND numbered_rows.installer_id IS NOT NULL'

    if status_filter and status_filter == 'client':
        query += ' AND numbered_rows.installer_id IS NULL AND a.status = "finished"'

    if installer_filter and installer_filter != 0:
        query += ' AND numbered_rows.installer_id = %s'
        filters.append(installer_filter)

    query += ' ORDER BY numbered_rows.id'

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, filters)
                results = await cur.fetchall()
                return [Equipment(id=r[0], rowNum=r[9], name=r[1], serialNumber=r[2], comment=r[3],
                                  applicationId=r[5], installerId=r[6], hash=r[8])
                        for r in results if results]


async def get_equipment_by_id(equipment_id: int):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT *
                    FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (ORDER BY id) AS row_num
                        FROM equipment
                    ) AS numbered_rows
                    WHERE id = %s
                ''', (equipment_id,))

                r = await cur.fetchone()
                return Equipment(id=r[0], name=r[1], serialNumber=r[2], comment=r[3],
                                 applicationId=r[5], installerId=r[6], hash=r[8], rowNum=r[-1]) if r else None


async def get_equipment_by_hash(hash: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''SELECT * FROM (
                                        SELECT *,
                                               ROW_NUMBER() OVER (ORDER BY id) AS row_num
                                        FROM equipment
                                    ) AS numbered_rows 
                                    WHERE hash = %s''', (hash,))
                r = await cur.fetchone()
                return Equipment(id=r[0], rowNum=r[-1], name=r[1], serialNumber=r[2], comment=r[3],
                                 applicationId=r[5], installerId=r[6], hash=r[8]) if r else []


async def create_equipment(equipment: NewEquipment):
    query = 'INSERT INTO equipment ('
    columns = []
    values = []
    params = []

    if equipment.name:
        columns.append("name")
        values.append("%s")
        params.append(equipment.name)
    if equipment.serialNumber:
        columns.append("serial")
        values.append("%s")
        params.append(equipment.serialNumber)
    if equipment.comment:
        columns.append("comment")
        values.append("%s")
        params.append(equipment.comment)
    if equipment.applicationId:
        columns.append("application_id")
        values.append("%s")
        params.append(equipment.applicationId)
    if equipment.installerId:
        columns.append("installer_id")
        values.append("%s")
        params.append(equipment.installerId)
    if equipment.hash:
        columns.append("hash")
        values.append("%s")
        params.append(equipment.hash)

    query += ", ".join(columns) + ") VALUES (" + ", ".join(values) + ")"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
                user_id = cur.lastrowid
                return user_id


async def update_equipment(equipment: Union[NewEquipment, UpdatedEquipment, dict[str, any]], equipment_id: int):
    query = 'UPDATE equipment SET '
    items = []
    params = []

    # Iterate through all keys in the input dictionary
    for key, value in equipment.items():
        # Map the field names from schema to database column names
        column_name = {
            "name": "name",
            "serialNumber": "serial",
            "comment": "comment",
            "applicationId": "application_id",
            "installerId": "installer_id",
            "hash": "hash"
        }.get(key)

        if column_name:
            items.append(f"{column_name} = %s")
            params.append(value)  # Add the value (can be None for SQL NULL)

    # Check if there's anything to update
    if not items:
        raise ValueError("No valid fields provided for update.")

    query += ", ".join(items)
    query += " WHERE id = %s;"
    params.append(equipment_id)

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()

async def set_equipment_installer(application_id: int, installer_id: int):
    query = "UPDATE equipment SET installer_id = %s WHERE application_id = %s"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (installer_id, application_id))
                await conn.commit()
    

async def reset_application_equipment(application_id: int):

    query = 'UPDATE equipment SET application_id = NULL, installer_id = NULL WHERE application_id = %s'

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (application_id,))
                await conn.commit()

async def reset_installer_equipment(application_id: int):

    query = 'UPDATE equipment SET installer_id = NULL WHERE application_id = %s'

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (application_id,))
                await conn.commit()

