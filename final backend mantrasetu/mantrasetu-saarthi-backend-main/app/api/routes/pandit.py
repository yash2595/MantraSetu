from typing import List, Optional

from fastapi import APIRouter, Form, File, UploadFile

from app.schemas.pandit_schema import PanditApplicationResponse
from app.controllers.pandit_controller import process_pandit_application, process_get_pandit_list

router = APIRouter(
    prefix="/pandit",
    tags=["Pandit"]
)

@router.get("/list")
async def get_pandit_list():
    return await process_get_pandit_list()


from pydantic import BaseModel
import uuid
from typing import Dict, Any
from app.database.pandit_db import save_pandit_draft, get_pandit_draft

class DraftRequest(BaseModel):
    draft_id: Optional[str] = None
    data: Dict[str, Any]

@router.post("/draft")
async def save_draft(request: DraftRequest):
    did = request.draft_id or str(uuid.uuid4())
    await save_pandit_draft(did, request.data)
    print(f"[BACKEND-DRAFT] Draft saved | draft_id={did}")

    # Send draft-resume email if email is available in draft data
    email_in_draft = request.data.get("panditEmail") or request.data.get("email")
    if email_in_draft:
        from app.services.email_service import send_draft_resume_email
        import os
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        draft_url = f"{base_url}/signup?role=pandit&draft={did}"
        pandit_name = (
            request.data.get("panditName")
            or f"{request.data.get('panditFirstName', '')} {request.data.get('panditLastName', '')}".strip()
        )
        print(f"[BACKEND-DRAFT] Sending draft-resume email to {email_in_draft}...")
        await send_draft_resume_email(
            to_email=email_in_draft,
            draft_url=draft_url,
            pandit_name=pandit_name,
        )
    else:
        print("[BACKEND-DRAFT] No email in draft data — skipping draft-resume email.")

    return {"status": "success", "draft_id": did}

@router.get("/draft/{draft_id}")
async def get_draft(draft_id: str):
    draft = await get_pandit_draft(draft_id)
    if not draft:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Draft not found")
    # Remove _id which is non-serializable ObjectId
    draft.pop("_id", None)
    return {"status": "success", "data": draft.get("data", {})}



@router.post("/apply", response_model=PanditApplicationResponse)
async def apply(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    languages: List[str] = Form(...),
    experience: str = Form(...),
    specialization: str = Form(...),
    gender: Optional[str] = Form(None),
    availability: Optional[str] = Form(None),
    service_areas: Optional[List[str]] = Form(None),
    education: Optional[str] = Form(None),
    gurukul: Optional[str] = Form(None),
    achievements: Optional[List[str]] = Form(None),
    bio: Optional[str] = Form(None),
    aadhaar_file: Optional[UploadFile] = File(None),
    certificate_file: Optional[UploadFile] = File(None),
    gallery_files: Optional[List[UploadFile]] = File(None),
):
    from fastapi import HTTPException
    if gallery_files:
        valid_files = [f for f in gallery_files if f.filename]
        if len(valid_files) > 7:
            raise HTTPException(status_code=400, detail="Too many gallery files. Max 7 allowed.")
        for gf in valid_files:
            if gf.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f".pdf not allowed for gallery files: {gf.filename}")
    return await process_pandit_application(
        name=name,
        email=email,
        phone=phone,
        password=password,
        confirm_password=confirm_password,
        city=city,
        state=state,
        languages=languages,
        experience=experience,
        specialization=specialization,
        gender=gender,
        availability=availability,
        service_areas=service_areas or [],
        education=education,
        gurukul=gurukul,
        achievements=achievements or [],
        bio=bio,
        aadhaar_file=aadhaar_file,
        certificate_file=certificate_file,
        gallery_files=gallery_files or [],
    )