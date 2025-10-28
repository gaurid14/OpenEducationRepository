from django import forms
from .models import User, ForumQuestion, ForumAnswer, ForumTopic


class ForumQuestionForm(forms.ModelForm):
    class Meta:
        model = ForumQuestion
        fields = ["title", "content", "topics"]  # topics is optional
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Your question title"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Describe your question..."}),
            "topics": forms.SelectMultiple(attrs={"class": "form-select"}),
        }

class ForumAnswerForm(forms.ModelForm):
    class Meta:
        model = ForumAnswer
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Write an answer or reply..."}),
        }


class ForumTopicForm(forms.ModelForm):
    class Meta:
        model = ForumTopic
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., CO1, Bloom’s, Ch-3"}),
        }

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_picture']
        labels = {'profile_picture': 'Upload a new profile picture'}