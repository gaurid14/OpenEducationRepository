# accounts/views/forum.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import ForumQuestion, ForumAnswer, ForumTopic
from ..forms import ForumQuestionForm, ForumAnswerForm, ForumTopicForm

# -------- List + Search + Filter (renders forum.html) --------
def forum_list_view(request):
    q = request.GET.get("q", "").strip()
    topic_id = request.GET.get("topic")

    questions = ForumQuestion.objects.select_related("author") \
        .prefetch_related("topics", "answers") \
        .annotate(answer_count=Count("answers")) \
        .order_by("-created_at")

    if q:
        questions = questions.filter(Q(title__icontains=q) | Q(content__icontains=q))

    if topic_id:
        questions = questions.filter(topics__id=topic_id)

    topics = ForumTopic.objects.annotate(num_questions=Count("questions")).order_by("-num_questions", "name")

    context = {
        "mode": "list",
        "questions": questions,
        "topics": topics,
        "q": q,
        "selected_topic": int(topic_id) if topic_id else None,
        "question_form": ForumQuestionForm(),
        "topic_form": ForumTopicForm(),
    }
    return render(request, "forum/forum.html", context)

# -------- Detail (renders same template) --------
def forum_detail_view(request, pk: int):
    question = get_object_or_404(
        ForumQuestion.objects.select_related("author").prefetch_related("topics", "answers__author", "answers__child_comments"),
        pk=pk
    )
    topics = ForumTopic.objects.all().order_by("name")

    context = {
        "mode": "detail",
        "question": question,
        "answer_form": ForumAnswerForm(),
        "topics": topics,
    }
    return render(request, "forum/forum.html", context)

# -------- Create question --------
@login_required
@require_POST
def forum_question_create(request):
    form = ForumQuestionForm(request.POST)
    if form.is_valid():
        question = form.save(commit=False)
        question.author = request.user
        question.save()
        form.save_m2m()
        messages.success(request, "Your question was posted.")
        return redirect("forum_detail", pk=question.pk)
    messages.error(request, "Please fix the errors below.")
    return redirect("forum_list")

# -------- Create answer (supports nested by parent id) --------
@login_required
@require_POST
def forum_answer_create(request, pk: int):
    question = get_object_or_404(ForumQuestion, pk=pk)
    form = ForumAnswerForm(request.POST)
    if form.is_valid():
        answer = form.save(commit=False)
        answer.author = request.user
        answer.question = question
        # parent handled by hidden field
        answer.save()
        messages.success(request, "Answer added.")
    else:
        messages.error(request, "Please provide valid content.")
    return redirect("forum_detail", pk=pk)

# -------- Upvotes: toggle (simple POST) --------
@login_required
@require_POST
def toggle_question_upvote(request, pk: int):
    question = get_object_or_404(ForumQuestion, pk=pk)
    if request.user in question.upvotes.all():
        question.upvotes.remove(request.user)
        state = "removed"
    else:
        question.upvotes.add(request.user)
        state = "added"
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok", "state": state, "count": question.total_upvotes})
    return redirect("forum_detail", pk=pk)

@login_required
@require_POST
def toggle_answer_upvote(request, pk: int):
    answer = get_object_or_404(ForumAnswer, pk=pk)
    if request.user in answer.upvotes.all():
        answer.upvotes.remove(request.user)
        state = "removed"
    else:
        answer.upvotes.add(request.user)
        state = "added"
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok", "state": state, "count": answer.total_upvotes})
    return redirect("forum_detail", pk=answer.question_id)

# -------- (Optional) Create a quick topic from the list page --------
@login_required
@require_POST
def forum_topic_create(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Only staff can create topics.")
    form = ForumTopicForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Topic created.")
    else:
        messages.error(request, "Invalid topic name.")
    return redirect("forum_list")
