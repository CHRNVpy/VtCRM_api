from typing import Optional, Union, Literal

from pydantic import BaseModel

from app.schema.error_schema import ErrorDetails


class ImageMetadata(BaseModel):
    ver: int
    applicationId: int
    installerId: int


class CrmImage(BaseModel):
    id: int
    name: str
    mimeType: str
    width: float
    height: float
    size: float
    path: str
    installerId: Optional[int]
    applicationId: Optional[int]


class ImageVersion(BaseModel):
    # ver: int
    entity: CrmImage


class ImageResponse(BaseModel):
    status: str
    data: Union[ImageVersion, ErrorDetails]
