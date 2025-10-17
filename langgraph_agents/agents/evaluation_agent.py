<<<<<<< HEAD
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
=======
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
>>>>>>> 7565647 (Initial project setup with Django, Postgres configs, and requirements.txt)
