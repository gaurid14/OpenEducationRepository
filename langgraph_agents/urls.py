<<<<<<< HEAD
from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_form, name="upload_form"),
    path("upload/", views.upload_file, name="upload_file"),
]
=======
from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_form, name="upload_form"),
    path("upload/", views.upload_file, name="upload_file"),
]
>>>>>>> 7565647 (Initial project setup with Django, Postgres configs, and requirements.txt)
