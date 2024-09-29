import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.v1.routes import routers as v1_routers
# from app.api.v2.routes import routers as v2_routers
from app.core.config import configs
from app.crud import init_db
from app.services.auth_service import VtCRM_HTTPException
from app.util.class_object import singleton


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db.init_db()
    yield


@singleton
class AppCreator:
    def __init__(self):
        # set app default
        self.app = FastAPI(
            title=configs.PROJECT_NAME,
            openapi_url=f"{configs.API}/openapi.json",
            version="0.0.1",
            lifespan=lifespan
        )

        # set cors
        if configs.BACKEND_CORS_ORIGINS:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=[str(origin) for origin in configs.BACKEND_CORS_ORIGINS],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # set routes
        @self.app.get("/")
        async def root():
            return {"status": "service is working"}

        self.app.include_router(v1_routers, prefix=configs.API_V1_STR)
        self.app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

        # self.app.include_router(v2_routers, prefix=configs.API_V2_STR)

        @self.app.exception_handler(VtCRM_HTTPException)
        async def custom_http_exception_handler(request: Request, exc: VtCRM_HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "status": "error",
                    "data": exc.error_details.model_dump()
                }
            )

        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            errors = []
            for error in exc.errors():
                error_detail = {
                    "location": error["loc"],
                    "message": error["msg"],
                    "error_type": error["type"]
                }
                errors.append(error_detail)

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "status": "error",
                    "data": errors
                }
            )


app_creator = AppCreator()
app = app_creator.app
