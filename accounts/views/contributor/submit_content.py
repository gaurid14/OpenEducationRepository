import asyncio
import threading

import docx
from asgiref.sync import async_to_sync
from django.shortcuts import render, redirect
from django.contrib import messages
from docx import Document

from accounts.models import Chapter, UploadCheck, Assessment, Question, Option, Course
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os
import tempfile
import json
import io

import pdfkit
import time

from langgraph_agents.graph.workflow import compiled_graph, graph
from langgraph_agents.services.drive_service import get_drive_service, get_or_create_drive_folder
from langgraph_agents.services.gemini_service import llm


@csrf_exempt
def upload_files(request):
    """Upload PDFs or videos to personal Drive. Create folders only if needed."""
    contributor_id = request.session.get('contributor_id', 101)
    course_id = request.session.get('course_id')
    chapter_number = request.session.get('chapter_number')
    chapter_name = request.session.get('chapter_name', 'structured_query_language')

    chapter_obj = Chapter.objects.filter(chapter_name__iexact=chapter_name).first()

    if request.method == "POST":
        service = get_drive_service()
        oer_content_id = get_or_create_drive_folder(service, "oer_content")

        # Upload PDFs if present
        pdf_files = request.FILES.getlist('pdf_file')
        if pdf_files:
            pdf_root_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS['pdf'], oer_content_id)
            contrib_pdf_folder = get_or_create_drive_folder(service, f"{contributor_id}_{course_id}_{chapter_number}", pdf_root_id)
            for pdf in pdf_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    for chunk in pdf.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                media = MediaFileUpload(tmp_path, mimetype='application/pdf')
                service.files().create(
                    body={'name': f"{contributor_id}_{pdf.name}", 'parents': [contrib_pdf_folder]},
                    media_body=media,
                    fields='id'
                ).execute()

                try:
                    os.remove(tmp_path)
                except Exception:
                    time.sleep(0.5)
                    try:
                        os.remove(tmp_path)
                    except Exception as e:
                        print(f"[ERROR] Could not delete temp file: {tmp_path}, {e}")

        # Upload Videos if present
        video_files = request.FILES.getlist('video_file')
        if video_files:
            video_root_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS['videos'], oer_content_id)
            contrib_video_folder = get_or_create_drive_folder(service, f"{contributor_id}_{course_id}_{chapter_number}", video_root_id)
            for video in video_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    for chunk in video.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                media = MediaFileUpload(tmp_path, mimetype='video/mp4')
                service.files().create(
                    body={'name': f"{contributor_id}_{video.name}", 'parents': [contrib_video_folder]},
                    media_body=media,
                    fields='id'
                ).execute()

                try:
                    os.remove(tmp_path)
                except Exception:
                    time.sleep(0.5)
                    try:
                        os.remove(tmp_path)
                    except Exception as e:
                        print(f"[ERROR] Could not delete temp file: {tmp_path}, {e}")

        # # Save DB record if chapter exists
        # if chapter_obj and (pdf_files or video_files):
        #     UploadCheck.objects.create(
        #         contributor_id=contributor_id,
        #         chapter=chapter_obj,
        #         evaluation_status=False
        #     )

        messages.success(request, "Files uploaded to Google Drive successfully!")
        # return redirect('upload_files')
        # Redirect back to original submission page
        course_id = request.session.get("course_id")
        chapter_id = request.session.get("chapter_id")
    return redirect(f'/dashboard/contributor/submit_content/?course_id={course_id}&chapter_id={chapter_id}')

    # return render(request, "contributor/submit_content.html")


# ---------------- EDITOR / DRAFT ---------------- #
@csrf_exempt
def contributor_editor(request):
    """Save drafts as HTML or final submissions as PDF in Google Drive."""
    service = get_drive_service()

    contributor_id = request.session.get('contributor_id', 101)
    course_id = request.session.get('course_id')
    chapter_number = request.session.get('chapter_number')
    chapter_name = request.session.get('chapter_name', 'structured_query_language')

    # Root folder for all OER content
    oer_root_id = get_or_create_drive_folder(service, "oer_content")
    drafts_root_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS['drafts'], oer_root_id)
    pdf_root_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS['pdf'], oer_root_id)

    # Contributor-specific folders
    drafts_folder_id = get_or_create_drive_folder(service, f"{contributor_id}_{course_id}_{chapter_number}", drafts_root_id)
    pdf_folder_id = get_or_create_drive_folder(service, f"{contributor_id}_{course_id}_{chapter_number}", pdf_root_id)

    if request.method == 'POST':
        action = request.POST.get('action')  # 'draft' or 'submitDraft'
        content = request.POST.get('notes', '')
        filename = request.POST.get('filename', 'draft.html')
        file_id = request.POST.get('file_id')  # New hidden input in form

        try:
            if action == 'draft':
                # Convert HTML content to DOCX
                doc = Document()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                for paragraph in soup.find_all(['p', 'div']):
                    text = paragraph.get_text(strip=True)
                    if text:
                        doc.add_paragraph(text)

                file_io = io.BytesIO()
                doc.save(file_io)
                file_io.seek(0)
                media = MediaIoBaseUpload(
                    file_io,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    resumable=True
                )

                user_filename = filename if filename.lower().endswith('.docx') else f"{filename}.docx"
                doc_filename = f"{contributor_id}_{user_filename}"

                if file_id:
                    # Update existing draft
                    service.files().update(
                        fileId=file_id,
                        media_body=media
                    ).execute()
                else:
                    # Create new draft
                    doc_filename = f"{contributor_id}_{user_filename}"
                    service.files().create(
                        body={'name': doc_filename, 'parents': [drafts_folder_id]},
                        media_body=media,
                        fields='id'
                    ).execute()

            elif action == 'submitDraft':
                # Save as PDF using xhtml2pdf
                from xhtml2pdf import pisa

                pdf_io = io.BytesIO()
                # Convert HTML to PDF
                result = pisa.CreatePDF(io.StringIO(content), dest=pdf_io)
                if result.err:
                    raise Exception("PDF generation failed")

                pdf_io.seek(0)
                media = MediaIoBaseUpload(pdf_io, mimetype='application/pdf', resumable=True)

                # Use same naming as draft
                # Ensure filename ends with .pdf
                user_filename = filename if filename.lower().endswith('.pdf') else f"{filename}.pdf"

                # Prepend contributor_id only if not already present
                if not user_filename.startswith(f"{contributor_id}_"):
                    pdf_filename = f"{contributor_id}_{user_filename}"
                else:
                    pdf_filename = user_filename


                # Upload PDF to Drive
                service.files().create(
                    body={'name': pdf_filename, 'parents': [pdf_folder_id]},
                    media_body=media,
                    fields='id'
                ).execute()

                # Delete the draft from Drive if editing an existing draft
                if file_id:
                    try:
                        service.files().delete(fileId=file_id).execute()
                    except Exception as e:
                        print(f"[WARNING] Could not delete draft {file_id}: {e}")

        except Exception as e:
            print(f"[ERROR] {action.capitalize()} upload failed: {e}")
            messages.error(request, f"Failed to save {action}: {e}")

    # Fetch existing drafts
    try:
        query = f"'{drafts_folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, createdTime)").execute()
        files = results.get('files', [])
    except Exception as e:
        files = []
        print(f"[ERROR] Failed to fetch drafts: {e}")

    course_id = request.session.get("course_id")
    chapter_id = request.session.get("chapter_id")
    return redirect(f'/dashboard/contributor/submit_content/?course_id={course_id}&chapter_id={chapter_id}')




# ---------------- LOAD FILE CONTENT ---------------- #
@csrf_exempt
def load_file(request):
    service = get_drive_service()
    file_id = request.GET.get('file_id')

    if not file_id:
        return JsonResponse({'error': 'file_id is required'}, status=400)

    try:
        request_file = service.files().get(fileId=file_id, fields='mimeType').execute()
        mime_type = request_file.get('mimeType', 'text/html')

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, service.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)

        print("Loading file_id:", file_id)
        print("Service object:", service)


        if 'text/html' in mime_type:
            content = fh.getvalue().decode('utf-8')
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            import docx
            doc = docx.Document(fh)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            # Join with <p> tags for TinyMCE
            content = ''.join(f'<p>{p}</p>' for p in paragraphs)
        else:
            content = f"<p>Cannot edit file of type {mime_type} in the editor.</p>"

        return JsonResponse({'content': content})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_drive_file(request):
    """Delete a Google Drive file permanently."""
    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        service = get_drive_service()
        try:
            service.files().delete(fileId=file_id).execute()
            return JsonResponse({'success': True, 'message': 'File deleted successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    # Redirect back to original submission page
    course_id = request.session.get("course_id")
    chapter_id = request.session.get("chapter_id")
    return redirect(f'/dashboard/contributor/submit_content/?course_id={course_id}&chapter_id={chapter_id}')
    # return JsonResponse({'success': False, 'message': 'Invalid request'})

@csrf_exempt
def submit_assessment(request):
    course_id = request.session.get("course_id")
    chapter_id = request.session.get("chapter_id")

    if not course_id or not chapter_id:
        messages.error(request, "Course or Chapter not found in session.")
        return redirect("/dashboard/contributor/submit_content/")

    course = Course.objects.get(id=course_id)
    chapter = Chapter.objects.get(id=chapter_id)

    if request.method == 'POST':
        # Extract all questions dynamically
        questions_data = []
        i = 0
        while f'questions[{i}][question]' in request.POST:
            q_text = request.POST[f'questions[{i}][question]']
            correct = int(request.POST[f'questions[{i}][correct]'])
            options = request.POST.getlist(f'questions[{i}][options][]')
            questions_data.append({'text': q_text, 'correct': correct, 'options': options})
            i += 1

        assessment = Assessment.objects.create(course=course, chapter=chapter, created_by=request.user)

        for q in questions_data:
            question = Question.objects.create(
                assessment=assessment,
                text=q['text'],
                correct_option=q['correct']
            )
            for opt_text in q['options']:
                Option.objects.create(question=question, text=opt_text)

    return redirect(f'/dashboard/contributor/submit_content/?course_id={course_id}&chapter_id={chapter_id}')




@csrf_exempt
def gemini_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            if not user_message:
                return JsonResponse({'error': 'No message provided'}, status=400)

            # Send to Gemini API
            response = llm.predict(user_message)

            return JsonResponse({'reply': response})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)


@csrf_exempt
def confirm_submission(request):
    """Handles final submission confirmation and triggers the LangGraph submission agent."""
    if request.method != "POST":
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        contributor_id = request.session.get('contributor_id')
        course_id = request.session.get('course_id')
        chapter_id = request.session.get('chapter_id')

        if not all([contributor_id, course_id, chapter_id]):
            return JsonResponse({'error': 'Missing session data'}, status=400)

        chapter_obj = Chapter.objects.get(id=chapter_id)
        chapter_name = chapter_obj.chapter_name
        chapter_number = chapter_obj.chapter_number

        service = get_drive_service()
        oer_root_id = get_or_create_drive_folder(service, "oer_content")

        # 🔹 Create or get subfolders for each content type
        pdf_root_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS['pdf'], oer_root_id)
        video_root_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS['videos'], oer_root_id)
        assess_root_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS['assessments'], oer_root_id)

        # 🔹 Contributor-specific folders
        pdf_folder_id = get_or_create_drive_folder(service, f"{contributor_id}_{course_id}_{chapter_number}", pdf_root_id)
        video_folder_id = get_or_create_drive_folder(service, f"{contributor_id}_{course_id}_{chapter_number}", video_root_id)
        assess_folder_id = get_or_create_drive_folder(service, f"{contributor_id}_{course_id}_{chapter_number}", assess_root_id)

        # 🔹 Prepare LangGraph state
        state = {
            "contributor_id": contributor_id,
            "chapter_name": chapter_name,
            "chapter_id": chapter_id,
            "course_id": course_id,
            "drive_folders": {
                "pdf": pdf_folder_id,
                "videos": video_folder_id,
                "assessments": assess_folder_id
            }
        }

        async def run_graph_async(state):
            await compiled_graph(state)  # compiled_graph is awaitable

        # ✅ Trigger submission agent
        from langgraph_agents.agents.submission_agent import submission_agent
        # ✅ Trigger submission agent in background thread
        threading.Thread(target=lambda: asyncio.run(run_graph_async(state))).start()

        return render(request, "contributor/after_submission.html", {
            "chapter_name": chapter_name,
            "contributor_id": contributor_id
        })

    except Exception as e:
        print(f"[ERROR] Final submission failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)
