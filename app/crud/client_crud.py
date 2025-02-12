import asyncio

import aiomysql

from app.core.config import configs
from app.schema.application_schema import ClientData


async def get_client_data(account):

    # query = '''SELECT
    #             contract.title AS account,
    #             contract.comment AS fullName,
    #             contract_parameter_type_phone.value AS phone,
    #             contract_parameter_type_2.address AS address,
    #             contract_parameter_type_3.email AS email
    #         FROM
    #             contract
    #         LEFT JOIN
    #             contract_parameter_type_phone ON contract_parameter_type_phone.cid = contract.id
    #         LEFT JOIN
    #             contract_parameter_type_2 ON contract_parameter_type_2.cid = contract.id
    #         LEFT JOIN
    #             contract_parameter_type_3 ON contract_parameter_type_3.cid = contract.id
    #         WHERE
    #             contract.title = %s'''

    query = '''
    SELECT 
        cpa.customer_id AS account,
        c.name AS fullName,
        cc.num AS phone,
        a.name AS address
    FROM 
        customer_portal_account cpa
    LEFT JOIN 
        customer c ON c.id = cpa.customer_id
    LEFT JOIN 
        address a ON a.id = cpa.customer_id
    LEFT JOIN 
        customer_contact cc ON cc.customer_id = cpa.customer_id 
    WHERE 
        cpa.customer_id = %s'''

    async with aiomysql.create_pool(**configs.EXT_DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (account,))
                client_data = await cur.fetchone()
                return ClientData(**client_data) if client_data else ClientData()
