from pydantic import BaseModel
from datetime import datetime


class Conversation(BaseModel):
    command: str
    response: str
    created_at: datetime = datetime.utcnow()