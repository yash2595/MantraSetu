from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

@router.get("/puja/list")
async def puja_list():
    return [
        {"id": "p1", "title": "Satyanarayan Puja", "category": "Home & Family", "description": "For wealth and prosperity", "price": 1100, "duration": "2.5 Hours", "rating": 4.8},
        {"id": "p2", "title": "Ganesh Puja", "category": "Wealth & Success", "description": "For removing obstacles", "price": 501, "duration": "2 Hours", "rating": 4.9}
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
