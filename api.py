from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import json
import shutil
from datetime import datetime
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.node_parser import SentenceSplitter
from main import get_llm_settings
from dotenv import load_dotenv
load_dotenv()

ngrok_key = os.getenv("NGROK_AUTHTOKEN")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_llm_settings(contect_window=4096, max_new_token=1024)

# Create a directory to store uploaded files
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatMessage(BaseModel):
    human: str
    assistant: str

class ChatRequest(BaseModel):
    chat_history: List[ChatMessage] = []
    message: str

# Dictionary to store document metadata and indices
doc_store = {
    "documents": {},  # Map file names to Document objects
    "indices": {},    # Map file names to indices
    "combined_index": None  # For all documents combined
}

def save_uploaded_file(uploaded_file: UploadFile) -> str:
    # Generate a unique filename using timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)

    return file_path, filename

def process_multiple_files(file_paths):
    """Process multiple files and create individual and combined indices"""
    all_documents = []
    doc_store["documents"] = {}
    doc_store["indices"] = {}
    
    # Process each file individually
    for file_path, original_name in file_paths:
        # Extract just the filename without timestamp
        if '_' in original_name:
            display_name = original_name.split('_', 1)[1]  # Get part after timestamp
        else:
            display_name = original_name
            
        # Load document
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        # Add metadata to track source file
        for doc in documents:
            doc.metadata["file_name"] = display_name
            
        # Store document and create individual index
        doc_store["documents"][display_name] = documents
        doc_store["indices"][display_name] = VectorStoreIndex.from_documents(
            documents=documents, 
            service_context=settings
        )
        all_documents.extend(documents)
    
    # Create combined index for all documents
    doc_store["combined_index"] = VectorStoreIndex.from_documents(
        documents=all_documents,
        service_context=settings
    )
    
    return doc_store["combined_index"].as_query_engine(
        response_mode=ResponseMode.TREE_SUMMARIZE
    )

def create_comparison_prompt(message, files):
    """Create a prompt specifically for comparing multiple resumes"""
    base_prompt = f"""
    I have {len(files)} different resumes/CVs to analyze. 
    
    The file names are: {', '.join(files)}
    
    For comparison purposes, please maintain awareness of which details come from which resume.
    When analyzing multiple resumes, please:
    1. Compare key skills, experience, and qualifications across candidates
    2. Identify relative strengths and weaknesses
    3. If asked to rank or rate candidates, provide clear justification
    
    My question is: {message}
    """
    return base_prompt

def chat_with_llama(chat_history: List[ChatMessage], message: str, file_paths: Optional[List[tuple]] = None):
    global query_engine
    
    # Initialize default query engine if needed
    if 'query_engine' not in globals():
        empty_documents = []
        index = VectorStoreIndex.from_documents(documents=empty_documents, service_context=settings)
        query_engine = index.as_query_engine()
    
    # Prepare context from chat history
    context = "\n".join([f"<|USER|>{item.human}\n<|ASSISTANT|>{item.assistant}" for item in chat_history[-10:]])
    
    # If this is a multiple file analysis, use special handling
    if file_paths and len(file_paths) > 1:
        # Process the files and create indices
        query_engine = process_multiple_files(file_paths)
        
        # Extract just the file names for the prompt
        file_names = [original_name.split('_', 1)[1] if '_' in original_name else original_name 
                      for _, original_name in file_paths]
        
        # Create comparison-specific prompt
        comparison_prompt = create_comparison_prompt(message, file_names)
        
        # For ranking/sorting queries, add structured instruction
        if any(keyword in message.lower() for keyword in 
              ["rank", "sort", "order", "best", "top", "compare", "better"]):
            comparison_prompt += """
            Please provide your analysis in a structured format:
            
            1. COMPARISON SUMMARY: Brief overview of how the resumes compare
            2. INDIVIDUAL ASSESSMENTS: For each resume, provide key strengths/weaknesses
            3. RANKING: If requested, provide a ranked list with justification for each position
            4. RECOMMENDATION: Which candidate(s) might be best suited and why
            """
        
        full_query = f"{context}\n<|USER|>{comparison_prompt}<|ASSISTANT|>"
    # Single file upload or continued conversation    
    else:
        # If a single file was uploaded, process it
        if file_paths and len(file_paths) == 1:
            file_path, original_name = file_paths[0]
            documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
            index = VectorStoreIndex.from_documents(documents=documents, service_context=settings)
            query_engine = index.as_query_engine()
            
        full_query = f"{context}\n<|USER|>{message}<|ASSISTANT|>"
    
    # Query the engine
    response = query_engine.query(full_query)
    return response

@app.get("/")
def home():
    return "Welcome to the Chat API!"

@app.post("/chat")
async def chat(request: Request, data: str = Form(...), file: Optional[UploadFile] = File(None)):
    try:
        chat_request = json.loads(data)
        message = chat_request.get('message', '')
        chat_history = [ChatMessage(**msg) for msg in chat_request.get('chat_history', [])]

        if not message:
            raise HTTPException(status_code=400, detail="No message provided")

        # Check for file parameter first
        file_paths = []
        if file and len(chat_history) == 0:
            file_path, original_name = save_uploaded_file(file)
            file_paths = [(file_path, original_name)]
            print(f"Single file saved at: {file_path}")
        
        # Check if request contains multiple files
        form_data = await request.form()
        multiple_files = []
        
        for key in form_data.keys():
            if key.startswith('file_') and form_data[key].filename:
                file_obj = form_data[key]
                file_path, original_name = save_uploaded_file(file_obj)
                multiple_files.append((file_path, original_name))
                print(f"Multiple file {key} saved at: {file_path}")
        
        if multiple_files:
            file_paths = multiple_files

        # Process the message with your LLM or chatbot logic here
        response = chat_with_llama(chat_history, message, file_paths if file_paths else None)
        return {"response": str(response)}
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@app.post("/new_chat")
async def new_chat():
    try:
        # Reset document store
        global doc_store
        doc_store = {
            "documents": {},
            "indices": {},
            "combined_index": None
        }
        
        # Delete all files in the upload directory
        for file in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return {"response": "Chat history and document store cleared."}
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Run without ngrok
    print("Server running at http://localhost:7000")
    uvicorn.run(app, host="0.0.0.0", port=7000)