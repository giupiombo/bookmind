import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Please ensure it's in your .env file or environment.")

os.environ['GOOGLE_API_KEY'] = api_key

client = genai.Client(api_key=api_key)
MODEL_ID = "gemini-2.0-flash"
