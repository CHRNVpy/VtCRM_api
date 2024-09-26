from fastapi import APIRouter, Depends, UploadFile, File, Form

from app.schema.images_schema import ImageResponse
from app.services.current_user_service import get_current_user
from app.services.images_service import ImagesService

router = APIRouter(
    tags=["images"],
)

service = ImagesService()


@router.post("/entity-image",
             response_model=ImageResponse,
             responses={401: {"description": "Invalid access token"}})
async def get_image(file: UploadFile = File(...), metadata: str = Form(...),
                    current_user: str = Depends(get_current_user)):
    response = await service.create_image(file, metadata, current_user)
    return ImageResponse(status='ok', data=response)
