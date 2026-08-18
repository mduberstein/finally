"""Chat router factory: `POST /api/chat` and `GET /api/chat/history`."""

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints
from starlette.concurrency import run_in_threadpool

from app.market.cache import PriceCache

from .models import MAX_MESSAGE_LENGTH
from .service import get_recent_messages, handle_chat_message


class ChatRequest(BaseModel):
    """The chat request body. Stripping before the minimum-length check is
    what makes a whitespace-only body a 422 rather than an empty prompt
    sent to the model; the maximum is a light denial-of-service
    mitigation. FastAPI returns 422 for both automatically."""

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MESSAGE_LENGTH),
    ]


def create_chat_router(cache: PriceCache) -> APIRouter:
    """Build the chat router bound to a specific cache.

    A factory (rather than a module-level router reading `request.app.state`)
    keeps these endpoints independently testable without a full app
    lifespan, matching `create_portfolio_router` and `create_watchlist_router`.
    """
    router = APIRouter()

    @router.post("/api/chat")
    async def chat(request: ChatRequest) -> dict:
        # `completion` is synchronous; calling it on the event loop would
        # stall every other request, including the SSE price stream, for
        # the whole round-trip.
        return await run_in_threadpool(handle_chat_message, request.message, cache)

    @router.get("/api/chat/history")
    async def chat_history() -> list[dict]:
        return await run_in_threadpool(get_recent_messages)

    return router
