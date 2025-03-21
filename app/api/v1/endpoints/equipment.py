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
                            name_filter: str = Query(None, description="name, serial or comment"),
                            status_filter: str = Query(None, description="client, installer or base"),
                            installer_filter: str = Query(None, description="installer name or surname"),
                            current_user: str = Depends(get_current_user)):
    equipment = await service.list_equipment(page, per_page, name_filter, status_filter, installer_filter)
    return EquipmentResponse(status='ok', data=equipment)


@router.post("/equipment",
             response_model=EquipmentResponse,
             responses={401: {"description": "Incorrect username or password"}})
async def create_equipment(new_item: NewEquipment,
                           current_user: str = Depends(get_current_user)):
    response = await service.add_equipment(new_item)
    return EquipmentResponse(status='ok', data=response)


@router.get("/equipment/{equipment_id}",
            response_model=EquipmentResponse,
            responses={401: {"description": "Incorrect username or password"}})
async def get_equipment(equipment_id: int,
                        current_user: str = Depends(get_current_user)):
    response = await service.get_equipment(equipment_id)
    return EquipmentResponse(status='ok', data=response)


@router.patch("/equipment/{equipment_id}",
              response_model=EquipmentResponse,
              responses={401: {"description": "Incorrect username or password"}})
async def update_equipment(equipment: UpdatedEquipment,
                           equipment_id: int,
                           current_user: str = Depends(get_current_user)):
    response = await service.update_equipment(equipment, equipment_id)
    return EquipmentResponse(status='ok', data=response)
