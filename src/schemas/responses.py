from pydantic import BaseModel
from typing import Optional, Any


class APIResponse(BaseModel):
    status: str
    content: Optional[Any] = None
