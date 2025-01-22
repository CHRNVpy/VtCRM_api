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
                       metadata: str = Form(ImageMetadata),
                       current_user: str = Depends(get_current_user)):
    try:
        parsed_metadata = ImageMetadata.model_validate_json(metadata)
    except ValidationError as e:
        raise VtCRM_HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                  error_details=ErrorDetails(code=str(e)))

    response = await service.create_image(file, parsed_metadata, current_user)
    return ImageResponse(status='ok', data=response)
