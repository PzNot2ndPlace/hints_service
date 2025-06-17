from fastapi import APIRouter
from ...services.hints_generator import hints_generation_service
from hints_service.schemas import *

router = APIRouter(prefix="/entities", tags=["Entities extraction"])


@router.post("/get_text_based_hint")
async def get_from_text(request: TextBasedHintRequest):
    return await hints_generation_service.generate_time_hint(request)
