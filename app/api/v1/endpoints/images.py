from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from pydantic import ValidationError

from app.schema.error_schema import ErrorDetails
from app.schema.images_schema import ImageResponse, ImageMetadata
from app.services.current_user_service import get_current_user
from app.services.images_service import ImagesService
from app.util.exception import VtCRM_HTTPException

router = APIRouter(
    tags=["images"],
)

service = ImagesService()


@router.post("/image",
             response_model=ImageResponse,
             responses={401: {"description": "Invalid access token"}})
async def upload_image(file: UploadFile = File(...),
                       current_user: str = Depends(get_current_user)):

    response = await service.create_image(file, current_user)
    return ImageResponse(status='ok', data=response)

@router.delete("/image/{image_id}",
             response_model=ImageResponse,
             responses={401: {"description": "Invalid access token"}})
async def delete_image(image_id: int,
                       current_user: str = Depends(get_current_user)):

    await service.delete_image(image_id)
    return ImageResponse(status='ok', data=None)
