import asyncio

import aiomysql

from app.core.config import configs
from app.schema.installer_schema import Installer, UpdateInstaller
from app.schema.user_schema import User


async def get_user(login: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT 
                          login,
                          password,
                          role AS role
                        FROM users
                        WHERE login = %s''', (login,))
                result = await cur.fetchone()
                return User(login=result[0], password=result[1], role=result[2]) if result else None


async def get_user_data(login: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT 
                          firstname AS firstname,
                          middlename AS middlename,
                          lastname AS lastname,
                          phone AS phone,
                          status As status,
                          role AS role,
                          id AS user_id
                        FROM users
                        WHERE login = %s''', (login,))
                result = await cur.fetchone()
                return Installer(firstname=result[0], middlename=result[1], lastname=result[2],
                                 phone=result[3], status=result[4], role=result[5], id=result[6])


async def save_refresh_token(user: str, password: str, refresh_token: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET refresh_token = %s WHERE login = %s AND password = %s",
                    (refresh_token, user, password)
                )
            await conn.commit()


async def is_refresh_token_valid(refresh_token: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM users WHERE refresh_token = %s",
                    (refresh_token,)
                )
                result = await cur.fetchone()
                return result is not None


async def get_users_version():
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT MAX(id) FROM users')
                result = await cur.fetchone()
                return result[0] if result else 0


async def get_installer_data_by_hash(hash: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT
                          login as login,
                          password as password, 
                          firstname AS firstname,
                          middlename AS middlename,
                          lastname AS lastname,
                          phone AS phone,
                          status As status,
                          role AS role,
                          id AS user_id
                        FROM users
                        WHERE hash = %s''', (hash,))
                result = await cur.fetchone()
                return Installer(login=result[0], password=result[1], firstname=result[2], middlename=result[3],
                                 lastname=result[4], phone=result[5], status=result[6], role=result[7],
                                 id=result[8]) if result else None


async def get_installer_data_by_id(installer_id: int):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT
                          login as login,
                          password as password, 
                          firstname AS firstname,
                          middlename AS middlename,
                          lastname AS lastname,
                          phone AS phone,
                          status As status,
                          role AS role,
                          id AS user_id
                        FROM users
                        WHERE id = %s''', (installer_id,))
                result = await cur.fetchone()
                return Installer(login=result[0], password=result[1], firstname=result[2], middlename=result[3],
                                 lastname=result[4], phone=result[5], status=result[6], role=result[7],
                                 id=result[8]) if result else None


async def hash_exists(hash: str):
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT hash FROM users WHERE role = "entity"''')
                results = await cur.fetchall()
                hashes = [r[0] for r in results if results]
                return True if hash in hashes else False


async def get_all_installers_data():
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT 
                          firstname AS firstname,
                          middlename AS middlename,
                          lastname AS lastname,
                          phone AS phone,
                          status As status,
                          role AS role,
                          id AS user_id
                        FROM users
                        WHERE role = 'installer'
                        ORDER BY 
                          CASE 
                            WHEN status = 'active' THEN 0 
                            ELSE 1 
                          END, 
                          lastname''')
                results = await cur.fetchall()
                return [Installer(firstname=result[0], middlename=result[1], lastname=result[2],
                                  phone=result[3], status=result[4], role=result[5], id=result[6])
                        for result in results if results]


async def update_installer(updated_installer: UpdateInstaller, installer_id: int):
    # Base query
    query = "UPDATE users SET "

    # Collect non-empty fields and their corresponding update statements
    updates = []
    params = []
    if updated_installer.firstname:
        updates.append(f"firstname = %s")
        params.append(updated_installer.firstname)
    if updated_installer.middlename:
        updates.append(f"middlename = %s")
        params.append(updated_installer.middlename)
    if updated_installer.lastname:
        updates.append(f"lastname = %s")
        params.append(updated_installer.lastname)
    if updated_installer.phone:
        updates.append(f"phone = %s'")
        params.append(updated_installer.phone)
    if updated_installer.status:
        updates.append(f"status = %s")
        params.append(updated_installer.status)
    if updated_installer.password:
        updates.append(f"password = %s")
        params.append(updated_installer.password)

    # Join updates with commas
    query += ", ".join(updates)

    # Add the WHERE clause to specify the entity to update
    query += f" WHERE id = {installer_id};"
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()

# print(asyncio.run(get_all_installers_data()))
