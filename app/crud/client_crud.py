import asyncio

import aiomysql
from watchfiles import awatch

from app.core.config import configs
from app.schema.application_schema import ClientData


async def get_client_data_felix(account):

    if account:
        account = int(account)

    # query = '''
    #         SELECT
    #             cpa.login AS account,
    #             c.name AS fullName,
    #             cc.num AS phone,
    #             a.name AS address
    #         FROM
    #             customer_portal_account cpa
    #         LEFT JOIN
    #             customer c ON c.id = cpa.customer_id
    #         LEFT JOIN
    #             connection co ON co.id = cpa.customer_id
    #         LEFT JOIN
    #             address a ON a.id = co.address_id
    #         LEFT JOIN
    #             customer_contact cc ON cc.customer_id = cpa.customer_id
    #         WHERE
    #             cpa.login = %s'''

    # query = '''
    #     SELECT
    #     CAST(SUBSTRING_INDEX(cn.num, '-', -1) AS UNSIGNED) AS account,
    #     c.name AS fullName,
    #     ad.name AS address,
    #     GROUP_CONCAT(cc.num SEPARATOR ',') AS phone
    #     FROM account AS a
    #     LEFT JOIN contract AS cn ON a.contract_id = cn.id
    #     LEFT JOIN customer AS c ON a.customer_id = c.id
    #     LEFT JOIN customer_contact AS cc ON cc.customer_id = c.id AND cc.customer_contact_type = 11
    #     LEFT JOIN connection AS con ON a.connection_id = con.id
    #     LEFT JOIN address AS ad ON con.address_id = ad.id
    #     WHERE cn.num LIKE %s
    #     GROUP BY cn.id, cn.num, a.contract_id, c.name, ad.name;'''

    query = '''
            SELECT
            pa.num AS account, 
            c.name AS fullName, 
            ad.name AS address, 
            GROUP_CONCAT(cc.num SEPARATOR ',') AS phone
            FROM account AS a
            LEFT JOIN contract AS cn ON a.contract_id = cn.id
            LEFT JOIN customer AS c ON a.customer_id = c.id
            LEFT JOIN customer_contact AS cc ON cc.customer_id = c.id AND cc.customer_contact_type = 11
            LEFT JOIN personal_account AS pa ON pa.id=a.personal_account_id
            LEFT JOIN connection AS con ON a.connection_id = con.id
            LEFT JOIN address AS ad ON con.address_id = ad.id
            WHERE pa.num = %s
            GROUP BY cn.id, c.name, cn.num, pa.num, ad.name;'''

    params = (account,)

    async with aiomysql.create_pool(**configs.EXT_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params)
                client_data = await cur.fetchone()
                return ClientData(**client_data) if client_data else ClientData()


async def get_client_data_bgbilling(account):

    query = '''SELECT
                contract.title AS account,
                contract.comment AS fullName,
                contract_parameter_type_phone.value AS phone,
                contract_parameter_type_2.address AS address,
                contract_parameter_type_3.email AS email
            FROM
                contract
            LEFT JOIN
                contract_parameter_type_phone ON contract_parameter_type_phone.cid = contract.id
            LEFT JOIN
                contract_parameter_type_2 ON contract_parameter_type_2.cid = contract.id
            LEFT JOIN
                contract_parameter_type_3 ON contract_parameter_type_3.cid = contract.id
            WHERE
                contract.title = %s'''

    async with aiomysql.create_pool(**configs.BGBILLING_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (account,))
                client_data = await cur.fetchone()
                return ClientData(**client_data) if client_data else ClientData()

async def get_client_data(account):


    data = await get_client_data_felix(account)

    if not data.account:

        data = await get_client_data_bgbilling(account)

    return data


async def get_clients_data_batch(client_ids):
    """Fetch multiple clients data in batch operations"""
    if not client_ids:
        return {}

    # Remove duplicates and None values
    unique_client_ids = list(set(filter(None, client_ids)))
    int_ids = [int(cid) for cid in unique_client_ids]

    client_data_map = {}

    felix_query = '''
        SELECT
        pa.num AS account, 
        c.name AS fullName, 
         ad.name AS address, 
        GROUP_CONCAT(cc.num SEPARATOR ',') AS phone
        FROM account AS a
        LEFT JOIN contract AS cn ON a.contract_id = cn.id
        LEFT JOIN customer AS c ON a.customer_id = c.id
        LEFT JOIN customer_contact AS cc ON cc.customer_id = c.id AND cc.customer_contact_type = 11
        LEFT JOIN personal_account AS pa ON pa.id=a.personal_account_id
        LEFT JOIN connection AS con ON a.connection_id = con.id
        LEFT JOIN address AS ad ON con.address_id = ad.id
        WHERE pa.num IN ({})
        GROUP BY cn.id, c.name, cn.num, pa.num, ad.name;'''.format(','.join(['%s'] * len(unique_client_ids)))

    # Add prefix before binding
    params = int_ids

    async with aiomysql.create_pool(**configs.EXT_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(felix_query, params)
                felix_clients = await cur.fetchall()

                # Process found clients
                felix_found_ids = set()
                for client in felix_clients:
                    if client and client.get('account'):
                        account = client['account']
                        felix_found_ids.add(account)
                        client_data_map[str(account)] = ClientData(**client)

    # For clients not found in Felix, try BGBilling
    not_found_ids = [cid for cid in int_ids if cid not in felix_found_ids]

    if not_found_ids:
        bgbilling_query = '''
            SELECT
                contract.title AS account,
                contract.comment AS fullName,
                contract_parameter_type_phone.value AS phone,
                contract_parameter_type_2.address AS address,
                contract_parameter_type_3.email AS email
            FROM
                contract
            LEFT JOIN
                contract_parameter_type_phone ON contract_parameter_type_phone.cid = contract.id
            LEFT JOIN
                contract_parameter_type_2 ON contract_parameter_type_2.cid = contract.id
            LEFT JOIN
                contract_parameter_type_3 ON contract_parameter_type_3.cid = contract.id
            WHERE
                contract.title IN ({})
        '''.format(','.join(['%s'] * len(not_found_ids)))

        async with aiomysql.create_pool(**configs.BGBILLING_DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(bgbilling_query, not_found_ids)
                    bgbilling_clients = await cur.fetchall()

                    # Process found clients from BGBilling
                    for client in bgbilling_clients:
                        if client and client.get('account'):
                            account = client['account']
                            client_data_map[account] = ClientData(**client)

    return client_data_map

# print(asyncio.run(get_client_data_felix(19326)))
# print(asyncio.run(get_clients_data_batch([19326, 9749, 9750, 11310])))
