import random

import aiomysql
from app.core.config import configs


async def init_db():
    async with aiomysql.create_pool(**configs.APP_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "CREATE TABLE IF NOT EXISTS users ("
                    "id INT AUTO_INCREMENT PRIMARY KEY, "
                    "firstname TEXT, "
                    "lastname TEXT, "
                    "middlename TEXT, "
                    "phone VARCHAR(20) UNIQUE, "
                    "status TEXT, "
                    "login VARCHAR(255) UNIQUE, "
                    "password TEXT, "
                    "role TEXT, "
                    "refresh_token VARCHAR(255) UNIQUE, "
                    "hash VARCHAR(255) UNIQUE)"
                )

                await cur.execute(
                    "CREATE TABLE IF NOT EXISTS app_pool ("
                    "id INT AUTO_INCREMENT PRIMARY KEY, "
                    "status TEXT, "
                    "installer_id INT, "
                    "FOREIGN KEY(installer_id) REFERENCES users(id))"

                )

                await cur.execute(
                    "CREATE TABLE IF NOT EXISTS applications ("
                    "id INT AUTO_INCREMENT PRIMARY KEY, "
                    "type TEXT, "
                    "client TEXT, "
                    "installer_id INT, "
                    "comment TEXT, "
                    "status TEXT, "
                    "install_date DATETIME, "
                    "app_pool_id INT, "
                    "FOREIGN KEY(installer_id) REFERENCES users(id), "
                    "FOREIGN KEY(app_pool_id) REFERENCES app_pool(id))"
                )

                await cur.execute(
                    "CREATE TABLE IF NOT EXISTS equipment ("
                    "id INT AUTO_INCREMENT PRIMARY KEY, "
                    "name TEXT, "
                    "serial VARCHAR(255) UNIQUE, "
                    "comment TEXT, "
                    "status TEXT, "
                    "application_id INT, "
                    "installer_id INT, "
                    "FOREIGN KEY(application_id) REFERENCES applications(id), "
                    "FOREIGN KEY(installer_id) REFERENCES users(id))"
                )

                await cur.execute(
                    "CREATE TABLE IF NOT EXISTS images ("
                    "id INT AUTO_INCREMENT PRIMARY KEY, "
                    "name TEXT, "
                    "mime_type TEXT, "
                    "width DECIMAL, "
                    "height DECIMAL, "
                    "size DECIMAL, "
                    "path TEXT, "
                    "application_id INT, "
                    "installer_id INT, "
                    "FOREIGN KEY(application_id) REFERENCES applications(id), "
                    "FOREIGN KEY(installer_id) REFERENCES users(id))"
                )
