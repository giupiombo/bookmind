from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import books

app = FastAPI(title="Book Library API")

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(books.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Book Library API"}
