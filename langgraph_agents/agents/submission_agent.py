import asyncio
import json
import os
import whisper
import mimetypes
from langchain.tools import tool

from langgraph_agents.services.drive_service import get_drive_service
from langgraph_agents.services.pdf_service import read_pdf
from langgraph_agents.services.gemini_service import llm
import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from accounts.models import UploadCheck, Chapter, ContentCheck
from django.conf import settings


from django.utils import timezone

def record_submission_to_db(contributor_id, chapter_id, drive_folders):
    """
    Called once the contributor confirms submission.
    Creates one UploadCheck + linked ContentCheck.
    """
    service = get_drive_service()
    now = timezone.now()  # Timestamp when Confirm Submission clicked

    # 🔹 Check which content folders actually have files
    content_flags = {"pdf": False, "video": False, "assessment": False}

    for folder_type, folder_id in drive_folders.items():
        if not folder_id:
            continue
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields="files(id)",
            pageSize=1
        ).execute()
        if results.get("files"):
            content_flags[folder_type] = True

    # 🔹 Get chapter object
    chapter_obj = Chapter.objects.filter(id=chapter_id).first()
    if not chapter_obj:
        print(f"[WARN] Chapter ID {chapter_id} not found.")
        return None

    # 🔹 Create UploadCheck record (with current time)
    upload = UploadCheck.objects.create(
        contributor_id=contributor_id,
        chapter=chapter_obj,
        evaluation_status=False,
        timestamp=now
    )

    # 🔹 Create ContentCheck record linked to this upload
    ContentCheck.objects.create(
        upload=upload,
        pdf=content_flags["pdf"],
        video=content_flags["video"],
        assessment=content_flags["assessment"]
    )

    print(f"[INFO] UploadCheck + ContentCheck created for contributor {contributor_id} at {now}")
    return upload



# 🔹 Integrate into LangGraph pipeline
@tool
async def submission_agent(state: dict) -> dict:
    """
    LangGraph node that finalizes submission after file processing.
    """
    contributor_id = state.get("contributor_id")
    chapter_id = state.get("chapter_id")
    drive_folders = state.get("drive_folders", {})  # ✅ dict: {"pdf": ..., "video": ..., "assessment": ...}

    # # (Optional) process files if you want to run extraction/summary steps
    # service = get_drive_service()
    # for folder_type, folder_id in drive_folders.items():
    #     if not folder_id:
    #         continue
    #     results = service.files().list(
    #         q=f"'{folder_id}' in parents and trashed=false",
    #         fields="files(id, name, mimeType)"
    #     ).execute()
    #
    #     for f in results.get("files", []):
    #         state["file_id"] = f["id"]
    #         state["metadata"] = {
    #             "name": f["name"],
    #             "mime_type": f["mimeType"],
    #             "folder_type": folder_type
    #         }
    #
    #         if f["mimeType"] == "application/pdf":
    #             state = extract_pdf_page_count(state)
    #             state = summarize_pdf_with_gemini(state)
    #         elif f["mimeType"].startswith("video/"):
    #             state = transcribe_video(state)

    # ✅ Record to DB (timestamp = confirm submission time)
    # record_submission_to_db(contributor_id, chapter_id, drive_folders)

    # Run DB insertion in background
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, record_submission_to_db, contributor_id, chapter_id, drive_folders)

    state["status"] = "submission_recorded"
    return state


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


