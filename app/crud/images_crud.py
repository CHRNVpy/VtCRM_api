import asyncio
from typing import Optional, List

import aiomysql

from app.core.config import configs
from app.schema.images_schema import CrmImage


async def get_images_version():
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT MAX(id) FROM images')
                result = await cur.fetchone()
                return result[0] if result[0] else 0


async def create_image(name: str, mime: str, width: float, height: float, size: float, path: str):
                       # application_id: Optional[int] = None, installer_id: Optional[int] = None):
    query = 'INSERT INTO images ('
    columns = []
    values = []
    params = []

    if name:
        columns.append("name")
        values.append("%s")
        params.append(name)
    if mime:
        columns.append("mime_type")
        values.append("%s")
        params.append(mime)
    if width:
        columns.append("width")
        values.append("%s")
        params.append(width)
    if height:
        columns.append("height")
        values.append("%s")
        params.append(height)
    if size:
        columns.append("size")
        values.append("%s")
        params.append(size)
    if path:
        columns.append("path")
        values.append("%s")
        params.append(path)
    # if application_id:
    #     columns.append("application_id")
    #     values.append("%s")
    #     params.append(application_id)
    # if installer_id:
    #     columns.append("installer_id")
    #     values.append("%s")
    #     params.append(installer_id)

    query += ", ".join(columns) + ") VALUES (" + ", ".join(values) + ")"

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()
                image_id = cur.lastrowid
                return image_id


async def get_image(image_id: int) -> CrmImage:
    query = 'SELECT * FROM images WHERE id = %s'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, image_id)
                r = await cur.fetchone()
                return CrmImage(id=r[0], name=r[1], mimeType=r[2], width=r[3], height=r[4], size=r[5],
                                path=r[6], installerId=r[8], applicationId=r[7])


async def get_images(application_id: int) -> list[CrmImage]:
    query = 'SELECT * FROM images WHERE application_id = %s'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, application_id)
                results = await cur.fetchall()
                return [CrmImage(id=r[0], name=r[1], mimeType=r[2], width=r[3], height=r[4], size=r[5],
                                 path=r[6], installerId=r[8], applicationId=r[7]) for r in results]

async def update_image(image_id: int, application_id: int, installer_id: int):
    query = 'UPDATE images SET application_id = %s, installer_id = %s WHERE id = %s'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (application_id, installer_id, image_id))
                await conn.commit()

async def reset_images(application_id: int):
    query = 'UPDATE images SET application_id = %s, installer_id = %s, step_id =%s WHERE application_id = %s'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (None, None, None, application_id))
                await conn.commit()

# print(asyncio.run(get_images(2)))
