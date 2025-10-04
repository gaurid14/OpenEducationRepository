# OER/accounts/forms.py

from django import forms
from .models import User

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_picture']
        labels = {'profile_picture': 'Upload a new profile picture'}