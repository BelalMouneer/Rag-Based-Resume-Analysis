# Resume-Docs-Based-RAG-LLM

A sophisticated AI-powered resume analysis platform that leverages Retrieval-Augmented Generation (RAG) to analyze, compare, and score resumes against job descriptions.

## Features

- **Resume Analysis**: Upload and analyze multiple resume/CV formats (PDF, DOCX, DOC, TXT)
- **Multi-Resume Comparison**: Compare multiple candidates side-by-side
- **ATS Scoring**: Match resumes against job descriptions to get an ATS compatibility score
- **Chat Interface**: Interactive Q&A with your resume documents
- **Chat History Management**: Create, switch between, and export chat sessions
- **Detailed Insights**: Get comprehensive analysis of skills, experience, and qualifications

## Requirements

- Python 3.8+
- Groq API key (for LLM access)
- Hugging Face token (for embedding models)
- Ngrok authtoken (for public URL access, optional)

## Setup

1. Clone the repository
2. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    venv\scripts\activate
    ```
3. Install dependencies:
    ```bash
    pip install -r requirement.txt
    ```
4. Create your environment file:
    ```bash
    cp .env.example .env
    ```
5. Edit the `.env` file with your API keys:
    ```
    HF_TOKEN = "your_huggingface_token_here"
    NGROK_AUTHTOKEN = "your_ngrok_authtoken_here"
    GROQ_API_KEY = "your_groq_api_key_here"
    API_URL = "http://localhost:7000"  # Default for local deployment
    ```

## Running the Application

### Start the backend server:
```bash
python main.py
```

This will:
- Start the FastAPI backend server
- Create a public URL using ngrok (if configured)
- Display the URL to access the application

### Start the Streamlit frontend:
```bash
streamlit run web.py
```

Access the application through your browser at the provided URL.

## Usage Guide

1. Upload one or multiple resumes through the interface
2. Toggle ATS Mode to compare resumes against job descriptions
3. Ask questions about the uploaded resumes
4. Export chat history for record-keeping
5. Create new chat sessions for different analysis tasks
