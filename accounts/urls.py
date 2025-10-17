<<<<<<< HEAD
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'), 
    path('register/', views.register_view, name='register'),
      path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
=======
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # Home page at "/"
    path('login/', views.login_view, name='login'), 
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_syllabus, name='upload_syllabus'),
    path('dashboard/contributor/', views.dashboard_view, name='contributor_dashboard'),
    path('dashboard/student/', views.dashboard_view, name='student_dashboard'),
]
>>>>>>> 7565647 (Initial project setup with Django, Postgres configs, and requirements.txt)
