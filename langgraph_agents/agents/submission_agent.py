<<<<<<< HEAD
import os
import whisper
import mimetypes
from langchain.tools import tool
from langgraph_agents.services.pdf_service import read_pdf
from langgraph_agents.services.gemini_service import llm

@tool
def extract_file_metadata(file_path: str) -> dict:
    """Extract metadata from an uploaded file."""
    if not file_path or not os.path.exists(file_path):
        return {"error": "File not found at path: " + file_path}

    mime_type, _ = mimetypes.guess_type(file_path)
    try:
        size_bytes = os.path.getsize(file_path)
        size_kb = round(size_bytes / 1024, 2)
    except Exception as e:
        return {"error": f"Could not get file size for {file_path}: {e}"}

    return {
        "file_name": os.path.basename(file_path),
        "mime_type": mime_type if mime_type else "unknown/unknown",
        "size_bytes": size_bytes,
        "size_kb": size_kb
    }

def extract_pdf_page_count(state: dict) -> dict:
    """If file is PDF, add page count and text."""
    file_path = state["file_path"]
    try:
        pages, text = read_pdf(file_path)
        state["metadata"]["page_count"] = pages
        state["pdf_text"] = text
    except Exception as e:
        state["metadata"]["pdf_read_error"] = f"Could not read PDF pages: {e}"
    return state

def summarize_pdf_with_gemini(state: dict) -> dict:
    """Summarize extracted PDF text."""
    if not state.get("pdf_text", "").strip():
        state["summary"] = "No text content could be extracted for summarization."
        return state

    try:
        prompt = f"Summarize the following document in 5-6 concise bullet points:\n\n{state['pdf_text']}"
        response = llm.invoke(prompt)
        state["summary"] = response.content
    except Exception as e:
        state["summary"] = f"Gemini summarization failed: {e}"
    return state

def transcribe_video(state: dict) -> dict:
    """
    Transcribes video files using free local Whisper model.
    """
    file_path = state["file_path"]

    # Load Whisper model (base is a good balance of speed & accuracy)
    model = whisper.load_model("base")

    try:
        result = model.transcribe(file_path)
        state["transcript"] = result["text"]
    except Exception as e:
        state["transcript"] = f"Transcription failed: {e}"

    return state
=======
import os
import whisper
import mimetypes
from langchain.tools import tool
from langgraph_agents.services.pdf_service import read_pdf
from langgraph_agents.services.gemini_service import llm

@tool
def extract_file_metadata(file_path: str) -> dict:
    """Extract metadata from an uploaded file."""
    if not file_path or not os.path.exists(file_path):
        return {"error": "File not found at path: " + file_path}

    mime_type, _ = mimetypes.guess_type(file_path)
    try:
        size_bytes = os.path.getsize(file_path)
        size_kb = round(size_bytes / 1024, 2)
    except Exception as e:
        return {"error": f"Could not get file size for {file_path}: {e}"}

    return {
        "file_name": os.path.basename(file_path),
        "mime_type": mime_type if mime_type else "unknown/unknown",
        "size_bytes": size_bytes,
        "size_kb": size_kb
    }

def extract_pdf_page_count(state: dict) -> dict:
    """If file is PDF, add page count and text."""
    file_path = state["file_path"]
    try:
        pages, text = read_pdf(file_path)
        state["metadata"]["page_count"] = pages
        state["pdf_text"] = text
    except Exception as e:
        state["metadata"]["pdf_read_error"] = f"Could not read PDF pages: {e}"
    return state

def summarize_pdf_with_gemini(state: dict) -> dict:
    """Summarize extracted PDF text."""
    if not state.get("pdf_text", "").strip():
        state["summary"] = "No text content could be extracted for summarization."
        return state

    try:
        prompt = f"Summarize the following document in 5-6 concise bullet points:\n\n{state['pdf_text']}"
        response = llm.invoke(prompt)
        state["summary"] = response.content
    except Exception as e:
        state["summary"] = f"Gemini summarization failed: {e}"
    return state

def transcribe_video(state: dict) -> dict:
    """
    Transcribes video files using free local Whisper model.
    """
    file_path = state["file_path"]

    # Load Whisper model (base is a good balance of speed & accuracy)
    model = whisper.load_model("base")

    try:
        result = model.transcribe(file_path)
        state["transcript"] = result["text"]
    except Exception as e:
        state["transcript"] = f"Transcription failed: {e}"

    return state
>>>>>>> 7565647 (Initial project setup with Django, Postgres configs, and requirements.txt)
