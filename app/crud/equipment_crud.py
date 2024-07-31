import asyncio

import aiomysql

from app.core.config import configs
from app.schema.equipment_schema import Equipment, NewEquipment, UpdatedEquipment


async def get_equipment_version():
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT MAX(id) FROM equipment')
                result = await cur.fetchone()
                return result[0] if result[0] else 0


async def get_all_equipment():
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT * 
                    FROM equipment
                    ORDER BY name''')
                results = await cur.fetchall()
                return [Equipment(id=r[0], name=r[1], serialNumber=r[2], comment=r[3], status=r[4],
                                  applicationId=r[5], installerId=r[6]) for r in results if results]


async def get_equipment_by_id(equipment_id: int):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT * FROM equipment WHERE id = %s', (equipment_id,))
                r = await cur.fetchone()
                return Equipment(id=r[0], name=r[1], serialNumber=r[2], comment=r[3], status=r[4],
                                 applicationId=r[5], installerId=r[6]) if r else None


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
    if equipment.status:
        columns.append("status")
        values.append("%s")
        params.append(equipment.status)
    if equipment.applicationId:
        columns.append("application_id")
        values.append("%s")
        params.append(equipment.applicationId)
    if equipment.installerId:
        columns.append("installer_id")
        values.append("%s")
        params.append(equipment.installerId)

    query += ", ".join(columns) + ") VALUES (" + ", ".join(values) + ")"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
                user_id = cur.lastrowid
                return user_id


async def update_equipment(equipment: UpdatedEquipment, equipment_id: int):
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
    if equipment.status:
        items.append(f"status = %s")
        params.append(equipment.status)
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
