import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

ENV: str = ""


class Configs(BaseSettings):
    # base
    ENV: str = os.getenv("ENV", "dev")
    API: str = "/api"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"
    PROJECT_NAME: str = "vtcrm-api"
    ENV_DATABASE_MAPPER: dict = {
        "prod": "vtcrm",
        "stage": "stage-vtcrm",
        "dev": "vt_crm",
        "test": "test-vtcrm",
    }
    DB_ENGINE_MAPPER: dict = {
        "postgresql": "postgresql",
        "mysql": "mysql+pymysql",
    }

    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # date
    DATETIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S"
    DATE_FORMAT: str = "%Y-%m-%d"

    # auth
    ALGORITHM: str = os.getenv("ALGORITHM", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_YEARS: int = 1

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # database
    DB: str = os.getenv("DB", "mysql")
    APP_DB_NAME: str = ENV_DATABASE_MAPPER[ENV]
    APP_DB_USER: str = os.getenv("APP_DB_USER")
    APP_DB_PASSWORD: str = os.getenv("APP_DB_PASS")
    APP_DB_HOST: str = os.getenv("APP_DB_HOST")
    APP_DB_PORT: int = os.getenv("APP_DB_PORT", "3306")
    DB_ENGINE: str = DB_ENGINE_MAPPER.get(DB, "mysql")

    APP_DB_CONFIG: dict = {
        'user': APP_DB_USER,
        'password': APP_DB_PASSWORD,
        'db': APP_DB_NAME,
        'host': APP_DB_HOST,
        'port': int(APP_DB_PORT),
    }

    EXT_DB_NAME: str = os.getenv("EXT_DB_NAME")
    EXT_DB_USER: str = os.getenv("EXT_DB_USER")
    EXT_DB_PASSWORD: str = os.getenv("EXT_DB_PASS")
    EXT_DB_HOST: str = os.getenv("EXT_DB_HOST")
    EXT_DB_PORT: int = os.getenv("EXT_DB_PORT", "3306")

    EXT_DB_CONFIG: dict = {
        'user': EXT_DB_USER,
        'password': EXT_DB_PASSWORD,
        'db': EXT_DB_NAME,
        'host': EXT_DB_HOST,
        'port': int(EXT_DB_PORT),
    }
#
#     # find query
#     PAGE = 1
#     PAGE_SIZE = 20
#     ORDERING = "-id"
#
#     class Config:
#         case_sensitive = True
#
#
# class TestConfigs(Configs):
#     ENV: str = "test"


configs = Configs()

if ENV == "prod":
    pass
elif ENV == "stage":
    pass
elif ENV == "test":
    setting = TestConfigs()
