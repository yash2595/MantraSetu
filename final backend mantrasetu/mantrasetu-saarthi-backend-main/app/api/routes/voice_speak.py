import base64
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(
    prefix="/voice",
    tags=["Voice"]
)

class SpeakRequest(BaseModel):
    text: str

@router.post("/speak-error")
async def speak_error(request: SpeakRequest):
    """Proxy text synthesis request to the AI Intent Engine and return raw audio stream."""
    try:
        async with httpx.AsyncClient() as client:
            ai_url = f"{settings.AI_SERVICE_URL}/voice/synthesize"
            payload = {
                "text": request.text,
                "language": "hinglish",
                "provider": "inworld"
            }
            resp = await client.post(ai_url, json=payload, timeout=settings.AI_SERVICE_TIMEOUT_SECONDS)
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"AI service returned error: {resp.text}"
                )
                
            data = resp.json()
            audio_base64 = data.get("audio_bytes")
            if not audio_base64:
                raise HTTPException(
                    status_code=500,
                    detail="AI service returned empty audio data"
                )
                
            audio_bytes = base64.b64decode(audio_base64)
            audio_format = data.get("format", "mp3")
            media_type = f"audio/{audio_format}"
            
            return Response(content=audio_bytes, media_type=media_type)
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to communicate with AI Intent Engine: {str(e)}"
        )
