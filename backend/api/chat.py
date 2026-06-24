from fastapi import APIRouter, HTTPException, status

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat_service import chat


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def create_chat_response(request: ChatRequest) -> ChatResponse:
    try:
        return await chat(request)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The research assistant could not complete this request. Please try again.",
        ) from None
