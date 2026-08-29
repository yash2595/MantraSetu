#!/usr/bin/env python3
import asyncio, os, sys, uuid
# Ensure project root is in sys.path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from app.voice.tts.factory import build_tts_provider
from app.voice.tts.schemas import VoiceSynthesisRequest

async def generate_bhagwan():
    provider = build_tts_provider(os.getenv('DEFAULT_TTS_PROVIDER', 'inworld'))
    request = VoiceSynthesisRequest(
        request_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        text='Bhagwan',
        voice='default',
    )
    audio_bytes = b''
    async for chunk in provider.stream(request):
        audio_bytes += chunk.data
        if chunk.is_final:
            break
    out_path = os.path.join(os.path.dirname(__file__), 'speech_name_r2.wav')
    with open(out_path, 'wb') as f:
        f.write(audio_bytes)
    print(f'Generated Bhagwan audio to {out_path}, {len(audio_bytes)} bytes')

if __name__ == '__main__':
    asyncio.run(generate_bhagwan())
