from fastapi import APIRouter, HTTPException
from ...services.hints_generator import hints_generation_service
from hints_service.schemas import *

router = APIRouter(prefix="/entities", tags=["Entities extraction"])


@router.post("/get_text_based_hint")
async def get_from_text(request: TextBasedHintRequest):
    try:
        hint = await hints_generation_service.generate_time_hint(request)
        if hint:
            return hint
        raise HTTPException(status_code=404, detail="No hints generated")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))