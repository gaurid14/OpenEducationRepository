import json
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from .submit_content import get_drive_service, get_or_create_drive_folder
from ...models import Expertise, Course, Chapter, UploadCheck


# @login_required
# def contributor_dashboard_view(request):
#     user = request.user
#
#     # --- Ensure it's a contributor ---
#     if user.role != "CONTRIBUTOR":
#         return render(request, "403.html", status=403)
#
#     # --- Get all expertise areas selected by this contributor ---
#     user_expertises = user.domain_of_expertise.all()
#
#     # --- Collect all unique related courses from those expertises ---
#     recommended_courses = Course.objects.filter(
#         expertises__in=user_expertises
#     ).distinct()
#
#     print("SQL:", str(recommended_courses.query))
#     print("Recommended Courses:", [c.course_name for c in recommended_courses])
#
#     # --- For each course, get its chapters to show dynamically ---
#     chapters_by_course = {
#         course.id: list(course.chapters.values("id", "chapter_name"))
#         for course in recommended_courses
#     }
#
#     context = {
#         "recommended_courses": list(
#             recommended_courses.values("id", "course_name")
#         ),
#         "chapters_by_course": chapters_by_course,
#     }
#
#     return render(request, "contributor/contributor_dashboard.html", context)



import json

@login_required
def contributor_dashboard_view(request):
    user = request.user

    if user.role != "CONTRIBUTOR":
        return render(request, "403.html", status=403)

    user_expertises = user.domain_of_expertise.all()

    recommended_courses = Course.objects.filter(
        expertises__in=user_expertises
    ).distinct()

    chapters_by_course = {
        course.id: list(course.chapters.values("id", "chapter_number", "chapter_name"))
        for course in recommended_courses
    }

    context = {
        "recommended_courses": list(
            recommended_courses.values("id", "course_name")
        ),
        "chapters_json": json.dumps(chapters_by_course),  # ✅ Properly serialized JSON
    }

    return render(request, "contributor/contributor_dashboard.html", context)



# @login_required
# def contributor_dashboard_view(request):
#     user = request.user
#
#     # Ensure it's a contributor
#     if user.role != "CONTRIBUTOR":
#         return render(request, "403.html", status=403)
#
#     user_expertises = user.domain_of_expertise.all()
#     recommended_courses = Course.objects.filter(
#         expertises__in=user_expertises
#     ).distinct()
#
#     # Contributor uploads
#     uploads = UploadCheck.objects.filter(contributor=user).select_related('chapter', 'chapter__course').order_by('-timestamp')
#
#     chapters_by_course = {course.id: list(course.chapters.values('id', 'chapter_name')) for course in recommended_courses}
#
#     context = {
#         "recommended_courses": recommended_courses,
#         "uploads": uploads,
#         "chapters_by_course": chapters_by_course,
#     }
#
#     return render(request, "contributor/contributor_dashboard.html", context)

@login_required
def contributor_profile(request):
    user = request.user

    if user.role != "CONTRIBUTOR":
        return render(request, "403.html", status=403)

    context = {
        "contributor": user
    }

    return render(request, "contributor/profile.html", context)

# def contributor_submit_content_view(request):
#     """
#     Contributor content submission view.
#     Displays chapter name dynamically.
#     """
#     course_id = request.GET.get("course_id")
#     chapter_id = request.GET.get("chapter_id")
#
#     # Fetch course and chapter safely
#     course = get_object_or_404(Course, id=course_id)
#     chapter = get_object_or_404(Chapter, id=chapter_id)
#
#     # Save in session (optional if you need later)
#     request.session["contributor_id"] = request.user.id
#     request.session["course_name"] = course.course_name
#     request.session["course_id"] = course.id
#     request.session["chapter_name"] = chapter.chapter_name
#     request.session["chapter_number"] = chapter.chapter_number
#     request.session["description"] = chapter.description
#
#     context = {
#         "course": course,
#         "chapter": chapter,
#     }
#
#     return render(request, "contributor/submit_content.html", context)



from django.http import JsonResponse
from googleapiclient.http import MediaIoBaseDownload

# def contributor_submit_content_view(request):
#     """
#     Contributor content submission view.
#     Displays chapter name dynamically and fetches all existing files.
#     """
#     course_id = request.GET.get("course_id")
#     chapter_id = request.GET.get("chapter_id")
#
#     # Fetch course and chapter safely
#     course = get_object_or_404(Course, id=course_id)
#     chapter = get_object_or_404(Chapter, id=chapter_id)
#
#     contributor_id = request.user.id
#
#     # 🔹 Check if UploadCheck already exists for this contributor & chapter
#     existing_upload = UploadCheck.objects.filter(
#         contributor_id=contributor_id,
#         chapter_id=chapter_id
#     ).first()
#
#     if existing_upload:
#         # ✅ Already submitted — redirect to thank-you/after-submission page
#         return render(request, "contributor/after_submission.html", {
#             "chapter_name": chapter.chapter_name,
#             "contributor_id": contributor_id,
#             "message": "You have already submitted this chapter’s content."
#         })
#
#     # Save in session
#     contributor_id = request.user.id
#     request.session["contributor_id"] = contributor_id
#     request.session["course_name"] = course.course_name
#     request.session["course_id"] = course_id
#     request.session["chapter_id"] = chapter_id
#     request.session["chapter_name"] = chapter.chapter_name
#     request.session["chapter_number"] = chapter.chapter_number
#     request.session["description"] = chapter.description
#
#     # Initialize Drive service
#     service = get_drive_service()
#     oer_root_id = get_or_create_drive_folder(service, "oer_content")
#
#     # Helper function to fetch files from folder
#     def get_files_from_folder(folder_type):
#         folder_name = f"{contributor_id}_{course.id}_{chapter.chapter_number}"
#         root_folder_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS[folder_type], oer_root_id)
#         # Try to get contributor-specific folder
#         query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{root_folder_id}' in parents and trashed=false"
#         folders = service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
#         files_list = []
#         if folders:
#             folder_id = folders[0]['id']
#             # Fetch files
#             results = service.files().list(q=f"'{folder_id}' in parents and trashed=false", fields="files(id, name, mimeType)").execute()
#             for f in results.get('files', []):
#                 files_list.append({
#                     'id': f['id'],
#                     'name': f['name'],
#                     'mimeType': f['mimeType'],
#                     'type': folder_type
#                 })
#         return files_list
#
#     files = []
#     for folder_type in ['drafts', 'pdf', 'videos', 'assessments']:
#         files.extend(get_files_from_folder(folder_type))
#
#     context = {
#         "course": course,
#         "chapter": chapter,
#         "files": files,
#     }
#
#     return render(request, "contributor/submit_content.html", context)


from google.auth.exceptions import RefreshError
import os
from django.contrib import messages

def contributor_submit_content_view(request):
    """
    Contributor content submission view.
    Displays chapter name dynamically and fetches all existing files.
    Handles expired/revoked Google tokens gracefully.
    """
    course_id = request.GET.get("course_id")
    chapter_id = request.GET.get("chapter_id")

    # Fetch course and chapter safely
    course = get_object_or_404(Course, id=course_id)
    chapter = get_object_or_404(Chapter, id=chapter_id)
    contributor_id = request.user.id

    # 🔹 Check if UploadCheck already exists
    existing_upload = UploadCheck.objects.filter(
        contributor_id=contributor_id,
        chapter_id=chapter_id
    ).first()

    if existing_upload:
        return render(request, "contributor/final_submission.html", {
            "chapter_name": chapter.chapter_name,
            "contributor_id": contributor_id,
            "message": "You have already submitted this chapter’s content."
        })

    # Save in session
    request.session.update({
        "contributor_id": contributor_id,
        "course_name": course.course_name,
        "course_id": course_id,
        "chapter_id": chapter_id,
        "chapter_name": chapter.chapter_name,
        "chapter_number": chapter.chapter_number,
        "description": chapter.description,
    })

    try:
        # 🔹 Initialize Drive service
        service = get_drive_service()
        oer_root_id = get_or_create_drive_folder(service, "oer_content")

        # --- Helper to fetch files from Drive ---
        def get_files_from_folder(folder_type):
            folder_name = f"{contributor_id}_{course.id}_{chapter.chapter_number}"
            root_folder_id = get_or_create_drive_folder(service, settings.GOOGLE_DRIVE_FOLDERS[folder_type], oer_root_id)

            # Find or create contributor folder
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{root_folder_id}' in parents and trashed=false"
            folders = service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
            files_list = []

            if folders:
                folder_id = folders[0]['id']
                results = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="files(id, name, mimeType)"
                ).execute()
                for f in results.get('files', []):
                    files_list.append({
                        'id': f['id'],
                        'name': f['name'],
                        'mimeType': f['mimeType'],
                        'type': folder_type
                    })
            return files_list

        files = []
        for folder_type in ['drafts', 'pdf', 'videos', 'assessments']:
            files.extend(get_files_from_folder(folder_type))

    except RefreshError as e:
        # 🔹 Token expired or revoked → delete it and ask user to reauthorize
        print(f"[ERROR] Google token invalid: {e}")
        token_path = os.path.join(settings.BASE_DIR, 'token.json')
        if os.path.exists(token_path):
            os.remove(token_path)
        messages.error(request, "⚠️ Your Google Drive session has expired. Please reconnect.")
        return redirect('contributor_submit_content_view')  # Will trigger re-login

    except Exception as e:
        print(f"[ERROR] Unexpected Drive issue: {e}")
        messages.error(request, f"An unexpected error occurred: {e}")
        files = []

    # Split description into topics on commas or semicolons
    raw_desc = chapter.description or ""
    topics = [t.strip() for t in re.split(r'[;,.]', raw_desc) if t.strip()]

    context = {
        "course": course,
        "chapter": chapter,
        "files": files,
        "topics": topics,
    }
    return render(request, "contributor/submit_content.html", context)
