# BookMind Backend

This is the backend of the BookMind application, developed using Python, Google Gemini, the Google AI Developer Kit (ADK), and FastAPI. Its primary goal is to <>.

## ✨ Features

- **<Topic>:** <explanation>

## 💭 How it works

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.9+
- `pip` (Python package installer)
- A Google Gemini API Key (obtainable from [Google AI Studio](https://aistudio.google.com/))

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/giupiombo/bookmind.git
    cd bookmind/backend
    ```

2.  **Create and activate a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On macOS/Linux
    # For Windows: .\venv\Scripts\activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your Google API Key:**
    Create a file named `.env` in the root directory of your project (where `main.py` is located) and add your Google Gemini API Key:
    ```dotenv
    GOOGLE_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY_HERE"
    ```
    **Important:** Replace `"YOUR_ACTUAL_GEMINI_API_KEY_HERE"` with your actual API key. Do not commit this file to public repositories.

### Running the API

1.  **Start the FastAPI server locally:**

    ```bash
    uvicorn main:app --reload
    ```

    The `--reload` flag will automatically restart the server on code changes.

2.  **Access the local API documentation:**
    Open your web browser and navigate to `http://localhost:8000/docs#/`. Here, you will find the interactive OpenAPI (Swagger UI) documentation, allowing you to test each API endpoint directly.

### 🌐 Live Deployment

This backend API is also deployed and hosted on **Render**. You can check out the live API documentation here:

- **Live API Docs:** <link>
