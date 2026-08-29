from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from bson import ObjectId
from app.database.mongodb import database

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

class StatusUpdateRequest(BaseModel):
    status: str
    rejection_reason: Optional[str] = None

@router.patch("/pandit/{pandit_id}/status")
async def update_pandit_status(
    pandit_id: str,
    request: StatusUpdateRequest,
    x_admin_key: str = Header(None)
):
    if not x_admin_key or x_admin_key != getattr(settings, "ADMIN_SECRET_KEY", "mantrasetu-admin-secret"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
        
    valid_statuses = ["pending", "approved", "rejected"]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    collection = database["pandit_applications"]
    try:
        obj_id = ObjectId(pandit_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Fetch pandit details BEFORE updating (to get email/name for notification)
    pandit_doc = await collection.find_one({"_id": obj_id})
    if not pandit_doc:
        raise HTTPException(status_code=404, detail="Pandit application not found")

    result = await collection.update_one(
        {"_id": obj_id},
        {"$set": {
            "status": request.status,
            "rejection_reason": request.rejection_reason
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pandit application not found")

    # Send status-update email notification
    pandit_email = pandit_doc.get("email")
    pandit_name = pandit_doc.get("name", "")
    if pandit_email and request.status in ("approved", "rejected"):
        from app.services.email_service import send_status_update_email
        print(
            f"[ADMIN] Sending status-update email to {pandit_email}"
            f" | status={request.status}"
        )
        await send_status_update_email(
            to_email=pandit_email,
            pandit_name=pandit_name,
            new_status=request.status,
            rejection_reason=request.rejection_reason,
        )
    else:
        print(
            f"[ADMIN] No email notification for status={request.status}"
            f" (email present: {bool(pandit_email)})"
        )

    return {"status": "success", "message": "Status updated successfully"}
