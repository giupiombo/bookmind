from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.genai import types
from config import client, MODEL_ID
from typing import Optional
import requests
import json
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Models ---

class BookRecommendation(BaseModel):
    title: str = Field(description="The title of the recommended book.")
    author: str = Field(description="The author of the recommended book.")
    cover_url: str = Field(description="A publicly accessible URL for the book's cover image.")
    reasoning: str = Field(description="A brief explanation of why this book was recommended.")

class RecommendationList(BaseModel):
    recommendations: list[BookRecommendation] = Field(description="A list of 3 book recommendations.")

class BookRequest(BaseModel):
    prompt: str = Field(description="A user prompt describing their book preferences.", example="A sci-fi book with a strong female lead.")

class AgentBookRecommendation(BaseModel):
    title: str = Field(description="The title of the recommended book.")
    author: str = Field(description="The author of the recommended book.")
    reasoning: str = Field(description="A brief explanation of why this book was recommended.")

class AgentRecommendationList(BaseModel):
    recommendations: list[AgentBookRecommendation] = Field(description="A list of 3 book recommendations.")

# --- Helper Functions ---

def lookup_cover(title: str, author: str) -> str:
    """
    Synchronously queries Open Library to find the most stable cover URL.
    This function MUST be called via run_in_threadpool in async endpoints.
    """
    try:
        url = "https://openlibrary.org/search.json"
        params = {"title": title, "author": author}

        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()

        if not data.get("docs"):
            return "https://placehold.co/200x300/e0e0e0/000000?text=Cover+Not+Found"

        doc = data["docs"][0]
        isbn = doc.get("isbn", [None])
        cover_id = doc.get("cover_i")

        if isbn and isinstance(isbn, list) and isbn[0]:
            clean_isbn = isbn[0].replace('-', '').replace(' ', '')
            return f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-L.jpg"
        elif cover_id:
            return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        else:
            return "https://placehold.co/200x300/e0e0e0/000000?text=Cover+Not+Found"

    except requests.exceptions.RequestException as e:
        print(f"HTTP Error looking up cover for {title} by {author}: {e}")
        return "https://placehold.co/200x300/e0e0e0/000000?text=Error+Loading"
    except Exception as e:
        print(f"General Error looking up cover for {title} by {author}: {e}")
        return "https://placehold.co/200x300/e0e0e0/000000?text=Error+Loading"


# --- API Endpoints ---

@app.post("/recommendations", response_model=RecommendationList)
async def get_recommendations(request: BookRequest):
    """
    Generates structured book recommendations from the AI, then programmatically
    fetches reliable cover URLs using Open Library.
    """
    system_instruction = (
      "You are a helpful and creative book recommendation agent. "
      "Your task is to provide exactly 3 distinct book recommendations based on the user's prompt. "
      "Crucially, you must provide the **exact title and author** for each book so that a cover image can be located by the external system. "
      "**DO NOT PROVIDE A COVER URL.** The URL will be fetched by a separate function using the title and author you provide."
      "The response must strictly adhere to the provided JSON schema."
    )

    agent_schema_dict = AgentRecommendationList.model_json_schema()

    try:
        # 1. Get Recommendations (Title, Author, Reasoning) from the AI
        response = await run_in_threadpool(
            client.models.generate_content,
            model=MODEL_ID,
            contents=request.prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=agent_schema_dict,
            )
        )

        agent_result = AgentRecommendationList.model_validate(json.loads(response.text))

        cover_tasks = []
        for item in agent_result.recommendations:
            task = run_in_threadpool(lookup_cover, title=item.title, author=item.author)
            cover_tasks.append(task)

        # 2. Concurrently fetch all cover URLs
        cover_urls = await asyncio.gather(*cover_tasks)

        final_recommendations = []

        # 3. Combine AI data with deterministic cover URL
        for item, cover_url in zip(agent_result.recommendations, cover_urls):
            final_recommendations.append(
                BookRecommendation(
                    title=item.title,
                    author=item.author,
                    reasoning=item.reasoning,
                    cover_url=cover_url
                )
            )

        # 4. Return the final structured result
        return RecommendationList(recommendations=final_recommendations)

    except Exception as e:
        print(f"An error occurred in /recommendations: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"AI Raw Response: {response.text}")
        raise HTTPException(status_code=500, detail="Error generating book recommendations.")

@app.get("/search-books")
def search_books(
    title: Optional[str] = Query(
        None,
        example="Verity",
        description="Title of the book to search for."
    ),
    author: Optional[str] = Query(
        None,
        example="Coleen Hoover",
        description="Author of the book to search for."
    )
):
    """
    Performs a direct search against Open Library for books and returns a list
    with associated cover URLs based on ISBN or cover ID.
    """
    if not title and not author:
        return {"error": "Please provide at least a title or author"}

    url = "https://openlibrary.org/search.json"
    params = {"title": title, "author": author}

    try:
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Open Library API error: {e}")


    books = []
    for doc in data.get("docs", [])[:20]:
        isbn_list = doc.get("isbn", [])
        cover_id = doc.get("cover_i")

        isbn = isbn_list[0] if isbn_list else None
        cover_url = None

        if isbn:
            clean_isbn = isbn.replace('-', '').replace(' ', '')
            cover_url = f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-L.jpg"
        elif cover_id:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

        books.append({
            "title": doc.get("title"),
            "author": doc.get("author_name", ["Unknown"])[0],
            "isbn": isbn,
            "cover_url": cover_url,
            "publish_year": doc.get("first_publish_year")
        })

    books = [b for b in books if b.get("isbn") or b.get("cover_url")]

    return {"count": len(books), "results": books[:10]}

@app.get("/get_cover")
def get_cover(
    title: str = Query(
        ...,
        example="The Housemaid"
    ),
    author: str = Query(
        "",
        example="Freida McFadden"
    )
):
    """
    Get single book cover.
    """
    cover_url = lookup_cover(title, author)

    return {
        "title": title,
        "author": author,
        "cover_url": cover_url
    }