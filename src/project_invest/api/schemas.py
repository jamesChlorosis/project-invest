from __future__ import annotations

from pydantic import BaseModel


class ResearchRunRequest(BaseModel):
    symbols: list[str] | None = None

