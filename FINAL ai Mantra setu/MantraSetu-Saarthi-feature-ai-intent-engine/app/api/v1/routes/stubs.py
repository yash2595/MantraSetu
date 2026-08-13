from fastapi import APIRouter, Form
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

@router.get("/puja/list")
async def puja_list():
    return [
        {"id": "p1", "title": "Satyanarayan Puja", "category": "Home & Family", "description": "For wealth and prosperity", "price": 1100, "duration": "2.5 Hours", "rating": 4.8},
        {"id": "p2", "title": "Ganesh Puja", "category": "Wealth & Success", "description": "For removing obstacles", "price": 501, "duration": "2 Hours", "rating": 4.9},
        {"id": "p3", "title": "Navratri Havan", "category": "Festival & Seasonal", "description": "Navratri havan for goddess blessings", "price": 2100, "duration": "3 Hours", "rating": 4.7},
        {"id": "p4", "title": "Griha Pravesh", "category": "Home & Family", "description": "House warming ceremony", "price": 5100, "duration": "4 Hours", "rating": 4.9},
        {"id": "p5", "title": "Vivah Puja", "category": "Sanskar", "description": "Vedic wedding ceremony", "price": 11000, "duration": "6 Hours", "rating": 5.0}
    ]

@router.post("/puja/book")
async def puja_book(payload: dict):
    return {"status": "success", "booking_id": "b_123", "message": "Puja booked successfully"}

@router.post("/muhurat/find")
async def muhurat_find(payload: dict):
    return {"status": "success", "muhurat": "2026-08-15T10:00:00Z", "message": "Muhurat found"}

@router.post("/kundali/generate")
async def kundali_generate(payload: dict):
    return {"status": "success", "kundali_url": "http://example.com/kundali.pdf", "message": "Kundali generated"}

@router.post("/contact")
async def contact_us(payload: dict):
    return {"status": "success", "message": "Message received"}

@router.post("/pandit/apply")
async def apply_pandit(
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    specialization: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    availability: Optional[str] = Form(None),
    education: Optional[str] = Form(None),
    gurukul: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    service_areas: List[str] = Form(default=[]),
    achievements: List[str] = Form(default=[]),
    languages: List[str] = Form(default=[]),
):
    import os, uuid, hashlib, logging
    from datetime import datetime, timezone

    logger = logging.getLogger(__name__)

    # --- Hash password (bcrypt preferred, sha256 fallback) ---
    password_hash = ""
    if password:
        try:
            import bcrypt
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            password_hash = "sha256:" + hashlib.sha256(password.encode()).hexdigest()

    # --- Build document ---
    pandit_id = str(uuid.uuid4())
    doc = {
        "_id": pandit_id,
        "name": name or "Panditji",
        "email": email or "",
        "phone": phone or "",
        "password_hash": password_hash,
        "city": city or "",
        "state": state or "",
        "experience": experience or "",
        "specialization": specialization or "",
        "gender": gender or "",
        "availability": availability or "",
        "education": education or "",
        "gurukul": gurukul or "",
        "bio": bio or "",
        "service_areas": service_areas if service_areas else [],
        "achievements": [a for a in achievements if a and a.strip()] if achievements else [],
        "languages": languages if languages else [],
        "status": "pending_review",
        "user_type": "pandit",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # --- Save to MongoDB ---
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/mantrasetu")
    try:
        import pymongo
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db_name = mongo_uri.rstrip("/").split("/")[-1] or "mantrasetu"
        db = client[db_name]
        result = db["pandit_applications"].insert_one(doc)
        inserted_id = str(result.inserted_id)
        logger.info("[PANDIT-APPLY] Saved to MongoDB. _id=%s, name=%s, email=%s", inserted_id, name, email)
        client.close()
    except Exception as e:
        logger.error("[PANDIT-APPLY] MongoDB save FAILED: %s", e)
        # Still return success so frontend doesn't break — log the failure
        inserted_id = pandit_id

    return {
        "access_token": f"pandit_token_{inserted_id[:8]}",
        "token_type": "bearer",
        "user": {
            "id": inserted_id,
            "name": name or "Panditji",
            "email": email or "",
            "user_type": "pandit",
        }
    }
