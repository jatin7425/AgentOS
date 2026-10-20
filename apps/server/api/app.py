from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AgentOS API", version="0.1.0")


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse()
