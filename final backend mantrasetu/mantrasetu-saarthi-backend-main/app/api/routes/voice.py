from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import httpx
import websockets
import asyncio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket_proxy(websocket: WebSocket):
    await websocket.accept()
    
    # Connect to AI service WebSocket
    ai_ws_url = settings.AI_SERVICE_URL.replace("http", "ws").replace("/api/v1", "") + "/ws/voice"
    logger.info(f"Connecting to AI WebSocket at {ai_ws_url}")
    
    try:
        async with websockets.connect(ai_ws_url) as ai_ws:
            
            async def forward_to_ai():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await ai_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.error(f"Error forwarding to AI: {e}")

            async def forward_to_client():
                try:
                    while True:
                        data = await ai_ws.recv()
                        await websocket.send_text(data)
                except websockets.exceptions.ConnectionClosed:
                    pass
                except Exception as e:
                    logger.error(f"Error forwarding to client: {e}")

            await asyncio.gather(
                forward_to_ai(),
                forward_to_client()
            )
            
    except Exception as e:
        logger.error(f"Failed to connect to AI WebSocket: {e}")
        await websocket.close()
