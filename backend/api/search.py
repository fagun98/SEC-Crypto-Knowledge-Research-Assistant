from fastapi import APIRouter, HTTPException, status

from backend.schemas.search import SearchRequest, SearchResponse
from backend.services.search_service import search


router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest) -> SearchResponse:
    try:
        return await search(request)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The knowledge search service is currently unavailable. Please try again.",
        ) from None
