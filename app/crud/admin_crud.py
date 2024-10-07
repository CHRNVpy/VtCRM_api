from typing import Union

import aiomysql

from app.core.config import configs
from app.schema.installer_schema import Installer, NewInstaller
from app.schema.user_schema import User


async def is_admin(login: str):
    query = 'SELECT role FROM users WHERE login = %s'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (login,))
                result = await cur.fetchone()  # is not None
                return True if result[0] == 'admin' else False


async def get_user_id(login: str):
    query = 'SELECT id FROM users WHERE login = %s'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (login,))
                r = await cur.fetchone()
                return r[0]


async def add_installer(installer: NewInstaller) -> None:
    query = ('INSERT INTO users (firstname, middlename, lastname, phone, status, login, password, role, hash) '
             'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)')
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (installer.firstname, installer.middlename, installer.lastname,
                                          installer.phone, installer.status, installer.login, installer.password,
                                          installer.role, installer.hash))
                await conn.commit()
                # user_id = cur.lastrowid
                # return user_id

async def get_version(table: str):
    query = f'SELECT {table} FROM versions'
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                r = await cur.fetchone()
                return r[0] if r else 0


async def update_version(table: str) -> int:
    query_select = f'SELECT {table} FROM versions'
    query_update = f'UPDATE versions SET {table} = %s'

    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Fetch the current users value
                await cur.execute(query_select)
                result = await cur.fetchone()

                current_value = result[0]

                new_value = current_value + 1

                await cur.execute(query_update, (new_value,))
                await conn.commit()

                return new_value
