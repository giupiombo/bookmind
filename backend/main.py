from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.genai import types
from config import client, MODEL_ID
from typing import Literal, List, Optional
import requests


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Models ---

## -- Book Recommendation --
class BookRecommendation(BaseModel):
    """A recommended book with a cover image URL."""
    title: str = Field(description="The title of the recommended book.")
    author: str = Field(description="The author of the recommended book.")
    cover_url: str = Field(description="A publicly accessible URL for the book's cover image.")
    reasoning: str = Field(description="A brief explanation of why this book was recommended.")

class RecommendationList(BaseModel):
    """A list of book recommendations."""
    recommendations: list[BookRecommendation] = Field(description="A list of 3 book recommendations.")

class BookRequest(BaseModel):
    prompt: str = Field(description="A user prompt describing their book preferences.", example="A sci-fi book with a strong female lead.")

## -- Search Author(s) / Book(s) --

class SearchRequest(BaseModel):
    """A request to search for a specific type of entity (Author or Book)."""
    type: Literal["author", "book"] = Field(description="The type of entity to search for: 'author' or 'book'.")
    text: str = Field(description="The query string (e.g., a book title, or an author's name).", example="Colleen Hoover")

class SearchResultList(BaseModel):
    """A list containing either book or author results, but not both."""
    books: List[str] = Field(default_factory=list, description="A list of up to 20 matching books. This is populated only if the request type was 'book'.")
    authors: List[str] = Field(default_factory=list, description="A list of up to 20 matching authors. This is populated only if the request type was 'author'.")

# --- API Endpoints ---

## -- Book Recommendation --
@app.post("/recommendations", response_model=RecommendationList)
async def get_recommendations(request: BookRequest):
    """
    Generates structured book recommendations based on a user's prompt using the Gemini model.
    """
    system_instruction = (
      "You are a helpful and creative book recommendation agent. "
      "Your task is to provide exactly 3 book recommendations based on the user's prompt. "
      "Crucially, you must find a publicly accessible, stable, and reliable cover image URL for each book. "

      "**STABILITY PROTOCOL:** "
      "To ensure the link works, you must find a URL that is a **direct link to the image file** (it must end in .jpg, .png, etc.) and is hosted on a public, non-commercial, or institutional domain."

      "**PRIORITY 1: OPEN LIBRARY COVERS API (ISBN) - WITH RELIABILITY CHECK** "
      "First, find the **ISBN-13** for the book. Prioritize the ISBN-13 corresponding to the **original or most widely circulated paperback edition**, as these are the most likely to have a cover available in the Open Library Covers API."
      "Then, generate the cover URL using the stable Open Library Covers API format: **https://covers.openlibrary.org/b/isbn/{ISBN-13}-L.jpg**. "
      "If this link is likely to return a blank/placeholder image (e.g., if the book is obscure or very new), proceed to Priority 2."

      "**PRIORITY 2: DIRECT PUBLIC DOMAIN/INSTITUTIONAL IMAGE** "
      "If the Open Library link is unreliable, search for the book cover image and specifically prioritize finding a **simple, direct link** (ending in .jpg, .png) from a major public institution (e.g., a university library, Library of Congress) or a reliable, simple content delivery network. "

      "**AVOID ALL:** Do not use links that contain complex API parameters (like 'zoom', 'source=gbs\_api', or 'SYxxx') or are hosted on primary retail domains (Amazon, Goodreads, B&N). These links always break or result in 'Image Not Available'."

      "The response must be in the specified JSON format."
    )

    schema_dict = RecommendationList.model_json_schema()

    try:
        # Call the Gemini API with structured output configuration
        response = await run_in_threadpool(
            client.models.generate_content,
            model=MODEL_ID,
            contents=request.prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema_dict,
            )
        )

        # The response.text will be a JSON string conforming to RecommendationList
        return RecommendationList.model_validate_json(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Error generating content from AI agent.")

## -- Book Search --
@app.post("/search", response_model=SearchResultList)
async def search(request: SearchRequest):
    """
    Searches for either books or authors based on a focused query and returns a list
    of up to 20 possible matches in the 'books' or 'authors' field, leaving the other empty.
    """
    search_type = request.type
    search_text = request.text

    # Customize the instruction based on the requested type
    if search_type == "book":
        instruction_focus = (
            "The user wants a list of **AUTHORS**. Search for authors that closely match the book title provided."
            "Populate the **'authors'** array with the top 20 results, ensuring you provide only the author's name. "
            "The 'books' array MUST be an empty list."
        )
    else: # type == "author"
        instruction_focus = (
            "The user wants a list of **BOOKS**. Search for books who were written by the given author. "
            "Populate the **'books'** array with the top 20 results, ensuring you provide only titles that were written by that author. "
            "The 'authors' array MUST be an empty list."
        )

    system_instruction = (
        "You are a focused book metadata search agent. "
        "Your task is to search the web for entities based on the user's specified search type and query. "
        "Return a list of up to 20 high-confidence results. "
        f"{instruction_focus}"

        "**CRITICAL:** Do not include any ISBN or cover URL in this result. "
        "The response must strictly adhere to the provided JSON schema, having one array populated and the other empty."
    )

    schema_dict = SearchResultList.model_json_schema()

    try:
        response = await run_in_threadpool(
            client.models.generate_content,
            model=MODEL_ID,
            contents=f"Search Type: {search_type}, Search Text: {search_text}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema_dict,
            )
        )
        return SearchResultList.model_validate_json(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Error performing book search.")

@app.get("/search-books")
def search_books(
    title: Optional[str] = Query(None),
    author: Optional[str] = Query(None)
):
    if not title and not author:
        return {"error": "Please provide at least a title or author"}

    url = "https://openlibrary.org/search.json"
    params = {"title": title, "author": author}
    res = requests.get(url, params=params)
    data = res.json()

    books = []
    for doc in data.get("docs", [])[:20]:
        isbn_list = doc.get("isbn", [])
        cover_id = doc.get("cover_i")

        isbn = isbn_list[0] if isbn_list else None
        cover_url = None

        if isbn:
            cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
        elif cover_id:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

        books.append({
            "title": doc.get("title"),
            "author": doc.get("author_name", ["Unknown"])[0],
            "isbn": isbn,
            "cover_url": cover_url,
            "publish_year": doc.get("first_publish_year")
        })

    books = [b for b in books if b["isbn"] or b["cover_url"]]

    return {"count": len(books), "results": books[:10]}

@app.get("/get_cover")
def get_cover(title: str, author: str = ""):
    # Query Open Library
    url = f"https://openlibrary.org/search.json?title={title}&author={author}"
    res = requests.get(url)
    data = res.json()

    if not data["docs"]:
        return {"error": "Book not found"}

    doc = data["docs"][0]
    isbn = doc.get("isbn", [None])[0]
    cover_id = doc.get("cover_i")

    cover_url = None
    if isbn:
        cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    elif cover_id:
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

    return {
        "title": doc.get("title"),
        "author": doc.get("author_name", ["Unknown"])[0],
        "isbn": isbn,
        "cover_url": cover_url
    }