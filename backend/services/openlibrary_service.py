import requests
from fastapi import HTTPException

def search_books(title: str , author: str ):
    """
    Searches Open Library for books and returns title, author, isbn, and cover URL.
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
