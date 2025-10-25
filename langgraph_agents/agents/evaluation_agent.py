import whisper

from langgraph_agents.services.gemini_service import llm
from langgraph_agents.services.pdf_service import read_pdf


def format_metadata(state: dict) -> dict:
    metadata_dict = state["metadata"]

    if "error" in metadata_dict:
        state["result"] = f"Error: {metadata_dict['error']}"
        return state

    output = (
        f"Filename: {metadata_dict['file_name']}, "
        f"Extension: {metadata_dict['mime_type']}, "
        f"Size: {metadata_dict['size_bytes']} bytes"
    )

    if "page_count" in metadata_dict:
        output += f", Page Count: {metadata_dict['page_count']} pages"

    if "summary" in state:
        output += f"\n\n📄 Gemini Summary:\n{state['summary']}"

    if "transcript" in state:
        output += f"\n\n🎤 Transcript:\n{state['transcript']}"

    state["result"] = output
    return state


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