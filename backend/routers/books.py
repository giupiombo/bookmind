from fastapi import APIRouter, Query
from typing import Optional
from services.openlibrary_service import search_books
from models.schemas import BookRequest, RecommendationList
from services.ai_service import get_recommendations_from_ai
from services.cover_service import lookup_cover

router = APIRouter(prefix="/books", tags=["Books"])

@router.post("/recommendations", response_model=RecommendationList)
async def get_recommendations(request: BookRequest):
    return await get_recommendations_from_ai(request.prompt)

@router.get("/search")
def search_books_endpoint(
    title: Optional[str] = Query(None, example="Verity"),
    author: Optional[str] = Query(None, example="Colleen Hoover")
):
    return search_books(title, author)

@router.get("/covers")
def get_cover(
    title: str = Query(..., example="The Housemaid"),
    author: str = Query("", example="Freida McFadden")
):
    cover_url = lookup_cover(title, author)
    return {"title": title, "author": author, "cover_url": cover_url}