# from fastapi import APIRouter, BackgroundTasks
# from services.cascading_service import process_cascading_sos

# router = APIRouter(prefix="/api/v1/sos", tags=["SOS Emergency"])

# @router.post("/trigger-cascading")
# async def trigger_cascading_sos(payload: dict, background_tasks: BackgroundTasks):
#     sos_id = payload.get("sosId", "TEST_SOS_001")
#     target_users = payload.get("targetUserIds", [])

#     # Background task fires without blocking API response
#     background_tasks.add_task(process_cascading_sos, sos_id, target_users)

#     return {
#         "status": "success",
#         "message": "Cascading SOS pipeline initiated in background! 🚀",
#         "total_targets": len(target_users)
#     }

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from services.cascading_service import process_cascading_sos

router = APIRouter(prefix="/api/v1/sos", tags=["SOS Emergency"])

# 🚀 Use Pydantic to automatically validate incoming JSON
class SOSPayload(BaseModel):
    sosId: str
    targetUserIds: list[str] # Or better: tier1_users: list[str], tier2_users: list[str]

@router.post("/trigger-cascading")
async def trigger_cascading_sos(payload: SOSPayload, background_tasks: BackgroundTasks):
    
    # Background task fires without blocking API response
    background_tasks.add_task(process_cascading_sos, payload.sosId, payload.targetUserIds)

    return {
        "status": "success",
        "message": "Cascading SOS pipeline initiated in background! 🚀",
        "total_targets": len(payload.targetUserIds)
    }