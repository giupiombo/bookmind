from pydantic import BaseModel, Field

# --- AI Recommendation Models ---
class AgentBookRecommendation(BaseModel):
    title: str = Field(description="The title of the recommended book.")
    author: str = Field(description="The author of the recommended book.")
    reasoning: str = Field(description="A brief explanation of why this book was recommended.")

class AgentRecommendationList(BaseModel):
    recommendations: list[AgentBookRecommendation] = Field(description="A list of 3 book recommendations.")

# --- API Response Models ---
class BookRecommendation(BaseModel):
    title: str = Field(description="The title of the recommended book.")
    author: str = Field(description="The author of the recommended book.")
    cover_url: str = Field(description="A publicly accessible URL for the book's cover image.")
    reasoning: str = Field(description="A brief explanation of why this book was recommended.")

class RecommendationList(BaseModel):
    recommendations: list[BookRecommendation] = Field(description="A list of 3 book recommendations.")

# --- Request Models ---
class BookRequest(BaseModel):
    prompt: str = Field(description="A user prompt describing their book preferences.", example="A sci-fi book with a strong female lead.")
