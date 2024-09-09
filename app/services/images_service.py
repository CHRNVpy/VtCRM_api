import io
import json
import mimetypes
from datetime import datetime
from pathlib import Path

import aiofiles
from PIL import Image
from fastapi import UploadFile, status

from app.crud.admin_crud import get_user_id
from app.crud.images_crud import get_images_version, create_image, get_image
from app.schema.error_schema import ErrorDetails
from app.schema.images_schema import ImageMetadata, ImageVersion
from app.util.exception import VtCRM_HTTPException


class ImagesService:

    def __init__(self):
        pass

    async def create_image(self, file: UploadFile, image_metadata, current_user: str):
        metadata_dict = json.loads(image_metadata)
        image_metadata = ImageMetadata(**metadata_dict)
        if image_metadata.ver != await get_images_version():
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Version mismatch"))
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type or not mime_type.startswith('image'):
            raise VtCRM_HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                      error_details=ErrorDetails(code="File is not an image"))

        content = await file.read()

        # Get image dimensions
        image = Image.open(io.BytesIO(content))
        width, height = image.size

        # Get current date
        current_date = datetime.now()
        year = current_date.strftime("%Y")
        month = current_date.strftime("%m")

        # Create the directory structure
        upload_dir = Path("uploads") / year / month
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate a unique filename to avoid overwrites
        file_extension = Path(file.filename).suffix
        unique_filename = f"{current_date.strftime('%Y%m%d_%H%M%S')}{file_extension}"

        # Save the file
        file_path = upload_dir / unique_filename
        async with aiofiles.open(file_path, 'wb') as buffer:
            await buffer.write(content)

        image_path = f"uploads/{year}/{month}/{unique_filename}"

        user_id = await get_user_id(current_user)

        image_id = await create_image(unique_filename, mime_type, width, height,
                                      file.size, image_path, installer_id=user_id,
                                      application_id=image_metadata.applicationId)

        return ImageVersion(ver=await get_images_version(), image=await get_image(image_id))
