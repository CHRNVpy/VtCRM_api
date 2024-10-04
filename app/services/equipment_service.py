from app.crud.equipment_crud import get_equipment_version, get_all_equipment, create_equipment, get_equipment_by_id, \
    update_equipment, equipment_hash_exists
from app.schema.equipment_schema import EquipmentList, NewEquipment, SingleEquipment, UpdatedEquipment
from app.schema.error_schema import ErrorDetails
from app.util.exception import VtCRM_HTTPException
from fastapi import status


class EquipmentService:

    def __init__(self):
        pass

    def paginate(self, data, page: int, limit: int):
        start = (page - 1) * limit
        end = start + limit
        return data[start:end]

    async def add_equipment(self, new_item: NewEquipment):
        if new_item.ver != await get_equipment_version():
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Version mismatch"))
        if await equipment_hash_exists(new_item.hash):
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Equipment hash exists"))
        new_equipment_id = await create_equipment(new_item)
        equipment = await get_equipment_by_id(new_equipment_id)
        return SingleEquipment(ver=await get_equipment_version(), entity=equipment)

    async def get_equipment(self, equipment_id: int):
        current_version = await get_equipment_version()
        if not equipment_id:
            raise VtCRM_HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                      error_details=ErrorDetails(code="Equipment ID required"))
        equipment = await get_equipment_by_id(equipment_id)
        if not equipment:
            raise VtCRM_HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                      error_details=ErrorDetails(code="Equipment ID not found"))
        return SingleEquipment(ver=current_version, entity=equipment)

    async def update_equipment(self, equipment: UpdatedEquipment, equipment_id: int):
        current_version = await get_equipment_version()
        if equipment.ver != current_version:
            raise VtCRM_HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                      error_details=ErrorDetails(code="Version mismatch"))
        if not equipment_id:
            raise VtCRM_HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                      error_details=ErrorDetails(code="Equipment ID required"))
        await update_equipment(equipment, equipment_id)
        equipment = await get_equipment_by_id(equipment_id)
        return SingleEquipment(ver=current_version, entity=equipment)

    async def list_equipment(self, page: int, limit: int, name_filter, status_filter, installer_filter):
        version = await get_equipment_version()
        equipment = await get_all_equipment(name_filter, status_filter, installer_filter)
        total_items = len(equipment)
        paginated_items = self.paginate(equipment, page, limit)
        total_pages = (total_items + limit - 1) // limit
        return EquipmentList(ver=version, entities=paginated_items, page=page, perPage=limit,
                                          pages=total_pages, totalRows=total_items)
