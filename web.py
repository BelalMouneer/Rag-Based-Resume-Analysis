import streamlit as st # type: ignore
import requests
import json
import base64
import datetime
import pandas as pd
from io import BytesIO
import os

from api import get_ats_score

# Initialize session state variables first - before anything else
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "file_info" not in st.session_state:
    st.session_state.file_info = None
if "current_file" not in st.session_state:
    st.session_state.current_file = None
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {"Default Chat": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Default Chat"
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "active_files" not in st.session_state:
    st.session_state.active_files = []
if "job_description" not in st.session_state:
    st.session_state.job_description = None
if "ats_mode" not in st.session_state:
    st.session_state.ats_mode = False
if "ats_scores" not in st.session_state:
    st.session_state.ats_scores = {}

def sync_uploaded_files_with_session():
    """Sync files in uploaded_files directory with session state variables"""
    # Check if the upload directory exists
    upload_dir = "uploaded_files"
    if not os.path.exists(upload_dir):
        return
        
    # Get list of files in the directory
    files_in_directory = os.listdir(upload_dir)
    
    # For each file in directory, check if it's in session state
    for filename in files_in_directory:
        filepath = os.path.join(upload_dir, filename)
        if os.path.isfile(filepath):
            # Handle timestamp prefix in filenames
            display_name = filename
            if '_' in filename:
                # Remove timestamp prefix (e.g., 20250419_111011_)
                parts = filename.split('_', 2)
                if len(parts) >= 3:
                    display_name = parts[2]  # Get the part after the timestamp
            
            # Check if we need to add to session state
            if display_name not in st.session_state.uploaded_files:
                with open(filepath, 'rb') as f:
                    file_content = f.read()
                    
                # Determine file type from extension
                file_type = "application/octet-stream"  # Default
                if display_name.lower().endswith('.pdf'):
                    file_type = "application/pdf"
                elif display_name.lower().endswith('.docx'):
                    file_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif display_name.lower().endswith('.doc'):
                    file_type = "application/msword"
                elif display_name.lower().endswith('.txt'):
                    file_type = "text/plain"
                    
                # Add to session state
                st.session_state.uploaded_files[display_name] = {
                    "name": display_name,
                    "content": file_content,
                    "type": file_type
                }

sync_uploaded_files_with_session()

def send_message(url, message, file_info=None, multiple_files=None):
    try:
        data = {
            "message": message,
            "chat_history": [
                {"human": msg["human"], "assistant": msg["assistant"]}
                for msg in st.session_state.chat_history
            ]
        }
        files = {}
        
        # Handle single file upload
        if file_info and not multiple_files:
            files = {
                "file": (file_info["name"], file_info["content"], file_info["type"])
            }
        
        # Handle multiple file uploads
        if multiple_files:
            for i, file_data in enumerate(multiple_files):
                files[f"file_{i}"] = (
                    file_data["name"], 
                    file_data["content"], 
                    file_data["type"]
                )

        # Send JSON data as a string in the 'data' field
        response = requests.post(
            f"{url}/chat",
            data={"data": json.dumps(data)},
            files=files
        )

        response.raise_for_status()  # This will raise an exception for HTTP errors

        result = response.json()
        # Add timestamp to messages
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        new_message = {"human": message, 'assistant': str(result["response"]), "timestamp": timestamp}
        
        # Add to current chat history
        st.session_state.chat_history.append(new_message)
        
        # Update in all_chats
        st.session_state.all_chats[st.session_state.current_chat] = st.session_state.chat_history
        
        return result["response"]
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            st.error(f"Response content: {e.response.content}")
        return "Sorry, there was an error processing your request."


def export_chat_history():
    """Export chat history as a text file"""
    if not st.session_state.chat_history:
        return None
    
    chat_export = "# Chat History Export\n"
    chat_export += f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    chat_export += f"## Files Analyzed\n"
    
    # Add list of files being analyzed
    if st.session_state.active_files:
        for file in st.session_state.active_files:
            chat_export += f"- {file}\n"
    elif st.session_state.current_file:
        chat_export += f"- {st.session_state.current_file}\n"
    
    chat_export += "\n## Conversation\n\n"
    
    for i, msg in enumerate(st.session_state.chat_history):
        timestamp = msg.get("timestamp", "N/A")
        chat_export += f"### Message {i+1} ({timestamp})\n"
        chat_export += f"**User**: {msg['human']}\n\n"
        chat_export += f"**Assistant**: {msg['assistant']}\n\n"
        chat_export += "---\n\n"
    
    return chat_export


def create_new_chat():
    """Create a new chat and switch to it"""
    # Generate a unique name for the new chat
    chat_name = f"Chat {len(st.session_state.all_chats) + 1}"
    st.session_state.all_chats[chat_name] = []
    st.session_state.current_chat = chat_name
    st.session_state.chat_history = []
    st.session_state.file_uploaded = False
    st.session_state.file_info = None
    st.session_state.current_file = None
    st.session_state.active_files = []
    
    try:
        requests.post(f"{st.session_state.backend_url}/new_chat")
    except:
        pass


# Streamlit app
st.set_page_config(
    page_title="MegaDev Intelligent System for Resumes Analysis",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    h1, h2, h3 {
        color: #2C3E50;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    .sidebar .sidebar-content {
        background-color: #2C3E50;
        color: white;
    }
    .stButton>button {
        background-color: #3498DB;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2980B9;
    }
    .chat-container {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 1rem;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .file-info {
        background-color: #e8f4fd;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .file-stats {
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        padding: 10px;
    }
    .stDataFrame {
        border-radius: 5px;
        overflow: hidden;
    }
    .success-msg {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .stSelectbox label, .stMultiSelect label {
        color: #2C3E50;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

api_url = os.getenv("API_URL", "http://localhost:7000")  # Default to localhost if not set
st.session_state["backend_url"] = api_url  # Store URL in session state

# App title with enhanced styling
st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0; background: linear-gradient(90deg, #3498db, #2c3e50); border-radius: 10px; margin-bottom: 20px;">
        <h1 style="color: white; font-size: 2.5rem; margin-bottom: 0.5rem;">MegaDev Intelligent System for Resumes Analysis</h1>
        <p style="color: #ecf0f1; font-size: 1.2rem;">Advanced AI-powered resume analysis and comparison platform</p>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"<div style='padding: 10px; background-color: #e2f0fd; border-radius: 5px; margin-bottom: 20px; display: flex; align-items: center;'><span style='color: #0366d6; margin-right: 10px;'>ℹ️</span><span>Connected to backend at <b>{api_url}</b></span></div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:

    st.header("🔧 Backend Configuration")
    
    st.header("🔍 ATS Mode")
    ats_toggle = st.toggle("Enable ATS Mode", value=st.session_state.ats_mode)

    if ats_toggle != st.session_state.ats_mode:
        st.session_state.ats_mode = ats_toggle
        # Clear previous scores when toggling
        st.session_state.ats_scores = {}
        st.rerun()

    if st.session_state.ats_mode:
        st.write("Upload a job description and compare with resumes")
        job_description = st.text_area(
            "Paste Job Description", 
            value=st.session_state.job_description if st.session_state.job_description else "",
            height=200
        )
        
        if job_description != st.session_state.job_description:
            st.session_state.job_description = job_description
            # Clear previous scores when job description changes
            st.session_state.ats_scores = {}

    st.header("💬 Chat Management")
    
    # Chat selection dropdown
    chat_options = list(st.session_state.all_chats.keys())
    selected_chat = st.selectbox("Select Chat", chat_options, index=chat_options.index(st.session_state.current_chat))
    
    if selected_chat != st.session_state.current_chat:
        st.session_state.current_chat = selected_chat
        st.session_state.chat_history = st.session_state.all_chats[selected_chat]
        st.rerun()
    
    # Start New Chat button in sidebar
    if st.button("Start New Chat", key="new_chat_sidebar"):
        create_new_chat()
        st.success("New chat created!")
        st.rerun()
    
    # Export chat functionality
    if len(st.session_state.chat_history) > 0:
        chat_export = export_chat_history()
        st.download_button(
            label="Download Chat History",
            data=chat_export,
            file_name=f"chat_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )

# Create a two-column layout
col1, col2 = st.columns([1, 3])

with col1:
    # File uploader section
    st.markdown("### 📤 Upload Documents")
    
    # Add toggle for single vs. multiple file mode
    upload_mode = st.radio("Upload Mode", ["Single File", "Multiple Files"])
    
    if upload_mode == "Single File":
        if not st.session_state.file_uploaded:
            uploaded_file = st.file_uploader("Choose a resume or document", type=[
                                            "txt", "pdf", "doc", "docx"])
            if uploaded_file is not None:
                st.session_state.file_uploaded = True
                st.session_state.file_info = {
                    "name": uploaded_file.name,
                    "content": uploaded_file.getvalue(),
                    "type": uploaded_file.type
                }
                st.session_state.current_file = uploaded_file.name
                st.session_state.active_files = [uploaded_file.name]
                
                # Add to uploaded_files dictionary too
                st.session_state.uploaded_files[uploaded_file.name] = {
                    "name": uploaded_file.name,
                    "content": uploaded_file.getvalue(),
                    "type": uploaded_file.type
                }
                
                st.success(f"File '{uploaded_file.name}' uploaded successfully!")
        else:
            st.info(f"📄 Current file: **{st.session_state.current_file}**")
            if st.button("Upload Different File"):
                st.session_state.file_uploaded = False
                st.rerun()
    else:
        # Multiple file uploader
        uploaded_files = st.file_uploader(
            "Choose resumes or documents", 
            type=["txt", "pdf", "doc", "docx"],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            # Store all uploaded files
            for uploaded_file in uploaded_files:
                file_info = {
                    "name": uploaded_file.name,
                    "content": uploaded_file.getvalue(),
                    "type": uploaded_file.type
                }
                st.session_state.uploaded_files[uploaded_file.name] = file_info
            
            # Display the list of uploaded files
            st.write("### Uploaded Files")
            
            # Use multiselect to manage active files
            file_names = list(st.session_state.uploaded_files.keys())
            selected_files = st.multiselect(
                "Select files to analyze",
                file_names,
                default=file_names[:min(5, len(file_names))]  # Default select up to 5 files
            )
            
            if selected_files:
                st.session_state.active_files = selected_files
                st.session_state.file_uploaded = True
                
                # Display info about selected files
                st.info(f"📄 Selected {len(selected_files)} files for analysis")
                
                if st.button("Process Selected Files"):
                    st.success(f"{len(selected_files)} files ready for analysis!")
            else:
                st.warning("Please select at least one file to analyze")
                st.session_state.file_uploaded = False
    
    # Show stats about uploaded files
    if hasattr(st.session_state, 'active_files') and st.session_state.active_files:
        st.write("### Document Stats")
        
        # Simple file statistics
        file_stats = pd.DataFrame({
            "File": st.session_state.active_files,
            "Type": [name.split('.')[-1].upper() for name in st.session_state.active_files],
        })
        st.dataframe(file_stats, hide_index=True)

    st.write("Active files:", st.session_state.active_files)
    st.write("Uploaded files keys:", list(st.session_state.uploaded_files.keys()))

with col2:
    # Display current chat name
    if st.session_state.active_files and len(st.session_state.active_files) > 1:
        st.markdown(f"### 💬 {st.session_state.current_chat} - Analyzing {len(st.session_state.active_files)} Files")
    else:
        st.markdown(f"### 💬 {st.session_state.current_chat}")
    
    # Add this before the chat container in col2
    if st.session_state.ats_mode and st.session_state.job_description:
        st.markdown("### 📊 ATS Matching Scores")
        
        if not st.session_state.active_files:
            st.warning("Please upload resumes to analyze")
        else:
            # Process button
            if st.button("Run ATS Analysis"):
                with st.spinner("Analyzing resumes against job description..."):
                    # Sync with filesystem first
                    sync_uploaded_files_with_session()
                    
                    # Debug information
                    st.write("Debug - Active files:", st.session_state.active_files)
                    st.write("Debug - Uploaded files keys:", list(st.session_state.uploaded_files.keys()))
                    
                    # If no active files but we have uploaded files, use them all
                    if not st.session_state.active_files and st.session_state.uploaded_files:
                        st.session_state.active_files = list(st.session_state.uploaded_files.keys())
                    
                    # Reset active files to only contain files that actually exist in uploaded_files
                    valid_active_files = [file for file in st.session_state.active_files 
                                         if file in st.session_state.uploaded_files]
                    
                    if len(valid_active_files) == 0:
                        st.error("No valid files found. Please re-upload your resumes.")
                    elif len(valid_active_files) != len(st.session_state.active_files):
                        st.warning(f"Some selected files weren't found in the uploaded files. Only analyzing {len(valid_active_files)} valid files.")
                        # Update active_files to only include valid files
                        st.session_state.active_files = valid_active_files
                        
                    # Process each valid file
                    for resume_name in valid_active_files:
                        # Skip if already scored
                        if resume_name in st.session_state.ats_scores:
                            continue
                        
                        try:
                            # Get the resume data
                            resume_data = st.session_state.uploaded_files[resume_name]
                            
                            # Get the score
                            score_data = get_ats_score(
                                st.session_state.job_description,
                                resume_data,
                                api_url
                            )
                            
                            # Store score data
                            st.session_state.ats_scores[resume_name] = score_data
                            
                        except Exception as e:
                            st.error(f"Error processing {resume_name}: {str(e)}")
            
            # Display scores if available
            if st.session_state.ats_scores:
                # Create score dataframe
                score_data = []
                for name, data in st.session_state.ats_scores.items():
                    score_data.append({
                        "Resume": name,
                        "Match Score": f"{data['score']}%" if data['score'] is not None else "N/A"
                    })
                    
                # Convert to DataFrame and sort by score
                score_df = pd.DataFrame(score_data)
                if not score_df.empty:
                    # Extract numeric scores for sorting
                    score_df["Numeric Score"] = score_df["Match Score"].apply(
                        lambda x: int(x.replace("%", "")) if x != "N/A" else 0
                    )
                    score_df = score_df.sort_values("Numeric Score", ascending=False)
                    # Drop the numeric column used for sorting
                    score_df = score_df.drop("Numeric Score", axis=1)
                    
                # Display the table
                st.dataframe(score_df, hide_index=True, use_container_width=True)
                
                # Add a section to view detailed analysis
                st.subheader("Detailed Analysis")
                selected_resume = st.selectbox(
                    "Select resume to view detailed analysis",
                    options=list(st.session_state.ats_scores.keys())
                )
                
                if selected_resume:
                    analysis = st.session_state.ats_scores[selected_resume]["full_analysis"]
                    st.markdown(f"### Analysis for {selected_resume}")
                    st.markdown(analysis)
    
    # Create chat container with custom styling
    chat_container = st.container(height=500)
    
    # Display chat messages with better formatting
    with chat_container:
        if st.session_state.chat_history:
            for i, message in enumerate(st.session_state.chat_history):
                # Get timestamp if available
                timestamp = message.get("timestamp", "")
                
                # User message with timestamp
                with st.chat_message("user"):
                    st.markdown(f"**{timestamp}**" if timestamp else "")
                    st.markdown(message.get("human"))
                    
                # Assistant message
                with st.chat_message("assistant"):
                    st.markdown(message.get("assistant"))
                
                # Add a subtle separator between message pairs
                if i < len(st.session_state.chat_history) - 1:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.2;'>", unsafe_allow_html=True)
        else:
            if st.session_state.active_files and len(st.session_state.active_files) > 1:
                st.markdown("*No messages yet. Start asking questions about the selected resumes!*")
            else:
                st.markdown("*No messages yet. Upload a document and start chatting!*")
    
    # Chat input
    if st.session_state.file_uploaded:
        if prompt := st.chat_input("What would you like to know about these resumes?"):
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Show a spinner while waiting for response
            with st.spinner("Analyzing..."):
                # Determine what files to send
                if len(st.session_state.chat_history) == 0:
                    if upload_mode == "Multiple Files" and st.session_state.active_files:
                        # Send multiple files on first message
                        multiple_files = [
                            st.session_state.uploaded_files[name] 
                            for name in st.session_state.active_files
                        ]
                        response = send_message(
                            api_url, 
                            prompt, 
                            None, 
                            multiple_files
                        )
                    else:
                        # Send single file on first message
                        response = send_message(
                            api_url, 
                            prompt, 
                            st.session_state.file_info
                        )
                else:
                    # After first message, just send the prompt
                    response = send_message(api_url, prompt)
            
            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(response)
            
            # Force refresh to show latest messages
            st.rerun()
    else:
        st.warning("⚠️ Please upload and select document(s) before starting the chat.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "<p>Resume-Docs-Based-RAG-LLM | Powered by Groq and Streamlit</p>"
    f"<p>Currently analyzing: {len(st.session_state.active_files) if hasattr(st.session_state, 'active_files') else 0} documents</p>"
    "</div>", 
    unsafe_allow_html=True
)
