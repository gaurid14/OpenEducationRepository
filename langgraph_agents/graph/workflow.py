<<<<<<< HEAD
from langgraph.graph import StateGraph
from langgraph.constants import END
from langgraph_agents.agents.submission_agent import extract_file_metadata, extract_pdf_page_count, summarize_pdf_with_gemini, transcribe_video
from langgraph_agents.agents.evaluation_agent import format_metadata

graph = StateGraph(dict)

def node_extract_metadata(state: dict) -> dict:
    state["metadata"] = extract_file_metadata.invoke(state["file_path"])
    return state

graph.add_node("extract_metadata", node_extract_metadata)
graph.add_node("pdf_page_count", extract_pdf_page_count)
graph.add_node("summarize_pdf", summarize_pdf_with_gemini)
graph.add_node("format_metadata", format_metadata)
graph.add_node("transcribe_media", transcribe_video)

def route_after_metadata(state: dict) -> str:
    mime_type = state["metadata"].get("mime_type", "")
    if mime_type.startswith("video/"):
        return "transcribe_media"
    elif mime_type == "application/pdf":
        return "pdf_page_count"
    else:
        return "format_metadata"

graph.set_entry_point("extract_metadata")
graph.add_conditional_edges("extract_metadata", route_after_metadata)
graph.add_edge("pdf_page_count", "summarize_pdf")
graph.add_edge("summarize_pdf", "format_metadata")
graph.add_edge("format_metadata", END)
graph.add_edge("transcribe_media", "format_metadata")

compiled_graph = graph.compile()
=======
from langgraph.graph import StateGraph
from langgraph.constants import END
from langgraph_agents.agents.submission_agent import extract_file_metadata, extract_pdf_page_count, summarize_pdf_with_gemini, transcribe_video
from langgraph_agents.agents.evaluation_agent import format_metadata

graph = StateGraph(dict)

def node_extract_metadata(state: dict) -> dict:
    state["metadata"] = extract_file_metadata.invoke(state["file_path"])
    return state

graph.add_node("extract_metadata", node_extract_metadata)
graph.add_node("pdf_page_count", extract_pdf_page_count)
graph.add_node("summarize_pdf", summarize_pdf_with_gemini)
graph.add_node("format_metadata", format_metadata)
graph.add_node("transcribe_media", transcribe_video)

def route_after_metadata(state: dict) -> str:
    mime_type = state["metadata"].get("mime_type", "")
    if mime_type.startswith("video/"):
        return "transcribe_media"
    elif mime_type == "application/pdf":
        return "pdf_page_count"
    else:
        return "format_metadata"

graph.set_entry_point("extract_metadata")
graph.add_conditional_edges("extract_metadata", route_after_metadata)
graph.add_edge("pdf_page_count", "summarize_pdf")
graph.add_edge("summarize_pdf", "format_metadata")
graph.add_edge("format_metadata", END)
graph.add_edge("transcribe_media", "format_metadata")

compiled_graph = graph.compile()
>>>>>>> 7565647 (Initial project setup with Django, Postgres configs, and requirements.txt)
