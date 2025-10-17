<<<<<<< HEAD
# OER/accounts/forms.py

from django import forms
from .models import User

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_picture']
=======
# OER/accounts/forms.py

from django import forms
from .models import User

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_picture']
>>>>>>> 7565647 (Initial project setup with Django, Postgres configs, and requirements.txt)
        labels = {'profile_picture': 'Upload a new profile picture'}