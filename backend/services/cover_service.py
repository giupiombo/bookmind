import requests

def lookup_cover(title: str, author: str) -> str:
    """
    Queries Open Library for a stable cover URL.
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

    except requests.exceptions.RequestException:
        return "https://placehold.co/200x300/e0e0e0/000000?text=Error+Loading"
