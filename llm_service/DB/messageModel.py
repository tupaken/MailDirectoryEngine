from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    """Lightweight message container used by the Python service."""

    id: int
    content: Optional[str] = None
    path: Optional[str] = None
