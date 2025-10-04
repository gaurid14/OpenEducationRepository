# OER/accounts/backends.py

from django.contrib.auth.backends import ModelBackend
# FIX: We are importing your custom User model directly
from .models import User 

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # FIX: We now use the directly imported User model
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        
        return None