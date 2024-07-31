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
