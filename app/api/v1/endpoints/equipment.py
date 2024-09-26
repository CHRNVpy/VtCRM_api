from fastapi import APIRouter, Depends, Query, Request

from app.schema.equipment_schema import PaginatedEquipmentResponse, NewEquipment, EquipmentResponse, UpdatedEquipment
from app.services.current_user_service import get_current_user
from app.services.equipment_service import EquipmentService

router = APIRouter(
    tags=["equipment"],
)

service = EquipmentService()


@router.get("/equipment-collection",
            response_model=EquipmentResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_all_equipment(page: int = Query(1, ge=1), per_page: int = Query(10, le=100),
                            current_user: str = Depends(get_current_user)):
    equipment = await service.list_equipment(page, per_page)
    return EquipmentResponse(status='ok', data=equipment)


@router.post("/equipment",
             response_model=EquipmentResponse,
             responses={401: {"description": "Incorrect username or password"}})
async def create_equipment(new_item: NewEquipment,
                           current_user: str = Depends(get_current_user)):
    response = await service.add_equipment(new_item)
    return EquipmentResponse(status='ok', data=response)


@router.get("/equipment",
            response_model=EquipmentResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_equipment(id: int = Query(None, description="Equipment id"),
                        current_user: str = Depends(get_current_user)):
    response = await service.get_equipment(id)
    return EquipmentResponse(status='ok', data=response)


@router.patch("/equipment",
              response_model=EquipmentResponse,
              responses={401: {"description": "Incorrect username or password"}})
async def update_equipment(equipment: UpdatedEquipment,
                           id: int = Query(0, description="Equipment id"),
                           current_user: str = Depends(get_current_user)):
    response = await service.update_equipment(equipment, id)
    return EquipmentResponse(status='ok', data=response)
