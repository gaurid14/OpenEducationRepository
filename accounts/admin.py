from django.contrib import admin
from .models import User,ForumTopic, ForumQuestion, ForumAnswer

@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(ForumQuestion)
class ForumQuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at")
    search_fields = ("title", "content")
    list_filter = ("created_at", "topics")

@admin.register(ForumAnswer)
class ForumAnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "author", "created_at", "parent")
    search_fields = ("content",)
    list_filter = ("created_at",)

# Register your models here.
admin.site.register(User)
