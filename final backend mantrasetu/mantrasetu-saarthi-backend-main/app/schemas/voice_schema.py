from pydantic import BaseModel


class VoiceCommandRequest(BaseModel):
    command: str