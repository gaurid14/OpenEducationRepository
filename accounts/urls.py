from django.urls import path
from .views import views
from .views.contributor import generate_expertise
from .views.contributor.contributor_dashboard import contributor_dashboard_view, contributor_submit_content_view, contributor_profile
from .views.contributor.submit_content import upload_files, load_file, contributor_editor, delete_drive_file, confirm_submission, submit_assessment, gemini_chat
from .views import forum as forum_views

urlpatterns = [
    path('', views.home_view, name='home'),  # Home page at "/"
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    # path('dashboard/', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_syllabus, name='upload_syllabus'),
    path('dashboard/contributor/', contributor_dashboard_view, name='contributor_dashboard'),
    path('dashboard/contributor/profile/', contributor_profile, name='contributor_profile'),
    path('dashboard/contributor/submit_content/', contributor_submit_content_view, name='contributor_submit_content_view'),
    path('dashboard/contributor/submit_content/upload', upload_files, name='upload_files'),
    path('dashboard/contributor/submit_content/uploadDraft', contributor_editor, name='contributor_editor'),
    path('dashboard/contributor/submit_content/load_file', load_file, name='load_file'),  # needed for JS
    path('dashboard/contributor/submit_content/delete_file', delete_drive_file, name='delete_drive_file'),  # needed for JS
    path('dashboard/contributor/submit_content/submit_assessment', submit_assessment, name='submit_assessment'),
    path('dashboard/contributor/submit_content/gemini_chat', gemini_chat, name='gemini_chat'),
    path('dashboard/contributor/submit_content/after_submission', confirm_submission, name='confirm_submission'),
    path('dashboard/student/', views.dashboard_view, name='student_dashboard'),
    path("forum/", forum_views.forum_list_view, name="forum_list"),
    path("forum/<int:pk>/", forum_views.forum_detail_view, name="forum_detail"),
    path("forum/create/", forum_views.forum_question_create, name="forum_question_create"),
    path("forum/<int:pk>/answer/", forum_views.forum_answer_create, name="forum_answer_create"),
    path("forum/<int:pk>/upvote/", forum_views.toggle_question_upvote, name="forum_question_upvote"),
    path("forum/answer/<int:pk>/upvote/", forum_views.toggle_answer_upvote, name="forum_answer_upvote"),
    path("forum/topic/create/", forum_views.forum_topic_create, name="forum_topic_create"),

]
