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
    query = '''SELECT * FROM equipment WHERE 1=1'''
    filters = []

    if name_filter:
        query += ' AND (name LIKE %s OR serial LIKE %s OR comment LIKE %s)'
        filters.extend([f'%{name_filter}%', f'%{name_filter}%', f'%{name_filter}%'])

    if status_filter and status_filter == 'base':
        query += ' AND installer_id IS NULL'

    if status_filter and status_filter == 'installer':
        query += ' AND installer_id IS NOT NULL'

    if installer_filter and installer_filter != 0:
        query += ' AND installer_id = %s'
        filters.append(installer_filter)

    query += ' ORDER BY id'

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, filters)
                results = await cur.fetchall()
                return [Equipment(id=r[0], name=r[1], serialNumber=r[2], comment=r[3],
                                  applicationId=r[5], installerId=r[6], hash=r[8])
                        for r in results if results]


async def get_equipment_by_id(equipment_id: int):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT * FROM equipment WHERE id = %s', (equipment_id,))
                r = await cur.fetchone()
                return Equipment(id=r[0], name=r[1], serialNumber=r[2], comment=r[3],
                                 applicationId=r[5], installerId=r[6], hash=r[8]) if r else None


async def get_equipment_by_hash(hash: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT * FROM equipment WHERE hash = %s', (hash,))
                r = await cur.fetchone()
                return Equipment(id=r[0], name=r[1], serialNumber=r[2], comment=r[3],
                                 applicationId=r[5], installerId=r[6], hash=r[8]) if r else None


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


async def update_equipment(equipment: Union[NewEquipment, UpdatedEquipment], equipment_id: int):
    query = 'UPDATE equipment SET '
    items = []
    params = []

    if equipment.name:
        items.append(f"name = %s")
        params.append(equipment.name)
    if equipment.serialNumber:
        items.append(f"serial = %s")
        params.append(equipment.serialNumber)
    if equipment.comment:
        items.append(f"comment = %s")
        params.append(equipment.comment)
    if equipment.applicationId:
        items.append(f"application_id = %s")
        params.append(equipment.applicationId)
    if equipment.installerId:
        items.append(f"installer_id = %s")
        params.append(equipment.installerId)

    query += ", ".join(items)
    query += f" WHERE id = {equipment_id};"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
