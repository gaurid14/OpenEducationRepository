# accounts/views/forum.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Prefetch
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import ForumQuestion, ForumAnswer, ForumTopic
from ..forms import ForumQuestionForm, ForumAnswerForm, ForumTopicForm
from django.views.decorators.http import require_POST
from django.http import JsonResponse

def _top_level_answers_qs():
    return ForumAnswer.objects.filter(parent__isnull=True).select_related("author")


# ---------- LIST (All discussions) ----------
def forum_home(request):
    q = request.GET.get("q", "").strip()
    topic_id = request.GET.get("topic")

    questions = (
        ForumQuestion.objects
        .select_related("author")
        .prefetch_related("topics")
        .annotate(answer_count=Count("answers"))
        .order_by("-created_at")
    )

    if q:
        questions = questions.filter(Q(title__icontains=q) | Q(content__icontains=q))

    if topic_id:
        questions = questions.filter(topics__id=topic_id)

    topics = ForumTopic.objects.annotate(num_questions=Count("questions")).order_by("-num_questions", "name")

    context = {
        "questions": questions,
        "topics": topics,
        "selected_topic": int(topic_id) if topic_id else None,
        "q": q,
        "q_form": ForumQuestionForm(),      # ask box
        "topic_form": ForumTopicForm(),     # (optional) quick topic create if you want
    }
    return render(request, "forum/list.html", context)


# ---------- DETAIL (single thread page with nested replies) ----------
def forum_detail(request, pk: int):
    question = (
        ForumQuestion.objects
        .select_related("author")
        .prefetch_related(
            "topics",
            Prefetch("answers", queryset=_top_level_answers_qs(), to_attr="top_answers"),
            "answers__child_comments__author",
        )
        .get(pk=pk)
    )
    return render(request, "forum/detail.html", {"question": question, "a_form": ForumAnswerForm()})


# ---------- CREATE QUESTION ----------
@login_required
@require_POST
def post_question(request):
    form = ForumQuestionForm(request.POST)
    if form.is_valid():
        q = form.save(commit=False)
        q.author = request.user
        q.save()
        form.save_m2m()
        messages.success(request, "Your question was posted.")
        return redirect("accounts:forum_detail", pk=q.pk)
    messages.error(request, "Please fix the errors below.")
    return redirect("accounts:forum_home")


# ---------- ANSWER (top-level) ----------
@login_required
@require_POST
def post_answer(request, question_id):
    question = get_object_or_404(ForumQuestion, pk=question_id)
    form = ForumAnswerForm(request.POST)
    if form.is_valid():
        ans = form.save(commit=False)
        ans.author = request.user
        ans.question = question
        ans.parent = None
        ans.save()
    return redirect("accounts:forum_detail", pk=question.pk)


# ---------- REPLY (nested) ----------
@login_required
@require_POST
def post_reply(request, question_id, parent_id):
    question = get_object_or_404(ForumQuestion, pk=question_id)
    parent = get_object_or_404(ForumAnswer, pk=parent_id, question=question)
    form = ForumAnswerForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.author = request.user
        reply.question = question
        reply.parent = parent
        reply.save()
    return redirect("accounts:forum_detail", pk=question.pk)


# ---------- UPVOTES (toggle) ----------
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
        return JsonResponse({"ok": True, "state": state, "count": question.upvotes.count()})
    return redirect("accounts:forum_home")


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
        return JsonResponse({"ok": True, "state": state, "count": answer.upvotes.count()})
    return redirect("accounts:forum_detail", pk=answer.question_id)

def toggle_answer_upvote(request, pk: int):
    ans = get_object_or_404(ForumAnswer, pk=pk)
    if request.user in ans.upvotes.all():
        ans.upvotes.remove(request.user)
    else:
        ans.upvotes.add(request.user)

    # optional AJAX support
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "count": ans.total_upvotes})
    return redirect("accounts:forum_detail", pk=ans.question_id)