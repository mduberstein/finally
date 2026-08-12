"""The assistant endpoints: one turn in, executed actions out."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.llm import LLMError
from app.llm import service as chat_service
from app.market import PriceCache

HISTORY_DEFAULT_LIMIT = 50


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ActionOut(BaseModel):
    """One executed or rejected action, rendered inline in the chat panel."""

    type: str
    status: str
    detail: str
    ticker: str


class ChatResponse(BaseModel):
    message: str
    actions: list[ActionOut]
    created_at: str


class ChatMessageOut(BaseModel):
    role: str
    content: str
    actions: list[ActionOut]
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]


def create_chat_router(cache: PriceCache) -> APIRouter:
    """Build the `/api/chat` router bound to a specific price cache.

    Handlers are plain `def` so FastAPI runs them in its threadpool: the model
    call blocks for a second or two, and blocking the event loop would stall
    every open SSE connection.
    """
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.post("", response_model=ChatResponse)
    def post_chat(body: ChatRequest) -> ChatResponse:
        """Answer one message, auto-executing any trades or watchlist changes."""
        try:
            result = chat_service.respond(cache, body.message)
        except LLMError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return ChatResponse.model_validate(result)

    @router.get("/history", response_model=ChatHistoryResponse)
    def get_history(
        limit: int = Query(HISTORY_DEFAULT_LIMIT, ge=1, le=500),
    ) -> ChatHistoryResponse:
        return ChatHistoryResponse(messages=chat_service.history(limit))

    return router
