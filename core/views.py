import io
import zipfile
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    ChapterCommentForm,
    ForumPostForm,
    ForumReplyForm,
    LoginForm,
    MangaCommentForm,
    RatingForm,
    RegistrationForm,
    SupportMessageForm,
)
from .models import (
    Chapter,
    ChapterComment,
    ChapterCommentReaction,
    ChapterRead,
    ForumPost,
    ForumReply,
    LastViewed,
    Manga,
    MangaComment,
    MangaCommentReaction,
    PrivateMessage,
    PrivateThread,
    Rating,
    ReadingListEntry,
    SearchKeyword,
    SupportThread,
)


def _user_is_banned(user):
    if not user.is_authenticated:
        return False
    profile = getattr(user, "profile", None)
    return profile and profile.banned


def home(request):
    popular = Manga.objects.order_by("-view_count")[:6]
    latest = Manga.objects.order_by("-created_at")[:12]
    manhwa = Manga.objects.filter(manga_type="manhwa").order_by("-created_at")[:8]
    manhua = Manga.objects.filter(manga_type="manhua").order_by("-created_at")[:8]
    manga = Manga.objects.filter(manga_type="manga").order_by("-created_at")[:8]
    last_viewed = []
    if request.user.is_authenticated:
        last_viewed = (
            LastViewed.objects.filter(user=request.user)
            .select_related("manga")
            .order_by("-last_viewed_at")[:6]
        )
    else:
        viewed_ids = request.session.get("last_viewed", [])
        if viewed_ids:
            last_viewed = Manga.objects.filter(id__in=viewed_ids)
    return render(
        request,
        "home.html",
        {
            "popular": popular,
            "latest": latest,
            "manhwa": manhwa,
            "manhua": manhua,
            "manga_list": manga,
            "last_viewed": last_viewed,
        },
    )


def manga_detail(request, slug):
    manga = get_object_or_404(Manga.objects.prefetch_related("categories"), slug=slug)
    order = request.GET.get("order", "asc")
    chapters = manga.chapters.all().order_by("-number" if order == "desc" else "number")
    new_threshold = timezone.now() - timedelta(days=3)
    new_chapter_ids = set(
        chapters.filter(published_at__gte=new_threshold).values_list("id", flat=True)
    )
    rating_average = manga.ratings.aggregate(avg=Avg("value"))["avg"]
    manga_comments = (
        MangaComment.objects.filter(manga=manga, parent__isnull=True)
        .annotate(
            likes_count=Count("reactions", filter=Q(reactions__is_like=True)),
            dislikes_count=Count("reactions", filter=Q(reactions__is_like=False)),
        )
        .select_related("user")
        .prefetch_related("replies")
        .order_by("-created_at")
    )
    chapter_reads = set()
    if request.user.is_authenticated:
        chapter_reads = set(
            ChapterRead.objects.filter(user=request.user, chapter__manga=manga).values_list(
                "chapter_id", flat=True
            )
        )
    comment_form = MangaCommentForm()
    rating_form = RatingForm()
    return render(
        request,
        "manga_detail.html",
        {
            "manga": manga,
            "chapters": chapters,
            "order": order,
            "new_chapter_ids": new_chapter_ids,
            "rating_average": rating_average,
            "manga_comments": manga_comments,
            "comment_form": comment_form,
            "rating_form": rating_form,
            "chapter_reads": chapter_reads,
        },
    )


@login_required
def add_manga_comment(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    if _user_is_banned(request.user):
        logout(request)
        messages.error(request, "تم حظر حسابك.")
        return redirect("login")
    form = MangaCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.manga = manga
        comment.save()
    return redirect("manga_detail", slug=slug)


@login_required
def react_manga_comment(request, comment_id):
    comment = get_object_or_404(MangaComment, id=comment_id)
    is_like = request.POST.get("action") == "like"
    MangaCommentReaction.objects.update_or_create(
        comment=comment, user=request.user, defaults={"is_like": is_like}
    )
    return redirect("manga_detail", slug=comment.manga.slug)


@login_required
def add_chapter_comment(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    if _user_is_banned(request.user):
        logout(request)
        messages.error(request, "تم حظر حسابك.")
        return redirect("login")
    form = ChapterCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.chapter = chapter
        comment.save()
    return redirect("chapter_reader", chapter_id=chapter_id)


@login_required
def react_chapter_comment(request, comment_id):
    comment = get_object_or_404(ChapterComment, id=comment_id)
    is_like = request.POST.get("action") == "like"
    ChapterCommentReaction.objects.update_or_create(
        comment=comment, user=request.user, defaults={"is_like": is_like}
    )
    return redirect("chapter_reader", chapter_id=comment.chapter.id)


@login_required
def add_rating(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    if _user_is_banned(request.user):
        logout(request)
        messages.error(request, "تم حظر حسابك.")
        return redirect("login")
    form = RatingForm(request.POST)
    if form.is_valid():
        Rating.objects.update_or_create(
            manga=manga, user=request.user, defaults={"value": form.cleaned_data["value"]}
        )
    return redirect("manga_detail", slug=slug)


@login_required
def add_to_list(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    list_type = request.POST.get("list_type")
    if list_type:
        ReadingListEntry.objects.update_or_create(
            user=request.user, manga=manga, defaults={"list_type": list_type}
        )
    return redirect("manga_detail", slug=slug)


@login_required
def toggle_chapter_read(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    mark = ChapterRead.objects.filter(user=request.user, chapter=chapter)
    if mark.exists():
        mark.delete()
    else:
        ChapterRead.objects.create(user=request.user, chapter=chapter)
    return JsonResponse({"success": True})


def chapter_reader(request, chapter_id):
    chapter = get_object_or_404(Chapter.objects.select_related("manga"), id=chapter_id)
    chapter.view_count += 1
    chapter.save(update_fields=["view_count"])
    Manga.objects.filter(id=chapter.manga_id).update(view_count=F("view_count") + 1)
    if request.user.is_authenticated:
        LastViewed.objects.update_or_create(user=request.user, manga=chapter.manga)
    else:
        viewed = request.session.get("last_viewed", [])
        if chapter.manga_id not in viewed:
            viewed.insert(0, chapter.manga_id)
        request.session["last_viewed"] = viewed[:10]
    comments = (
        ChapterComment.objects.filter(chapter=chapter, parent__isnull=True)
        .annotate(
            likes_count=Count("reactions", filter=Q(reactions__is_like=True)),
            dislikes_count=Count("reactions", filter=Q(reactions__is_like=False)),
        )
        .select_related("user")
        .prefetch_related("replies")
        .order_by("-created_at")
    )
    comment_form = ChapterCommentForm()
    return render(
        request,
        "chapter_reader.html",
        {
            "chapter": chapter,
            "images": chapter.images.all(),
            "comments": comments,
            "comment_form": comment_form,
        },
    )


def download_chapter(request, chapter_id):
    chapter = get_object_or_404(Chapter.objects.select_related("manga"), id=chapter_id)
    folder_name = f"{chapter.manga.title}، الفصل: {chapter.number}"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for image in chapter.images.all():
            name_parts = image.image.name.rsplit(".", 1)
            extension = name_parts[-1] if len(name_parts) > 1 else "jpg"
            filename = f"{folder_name}/{image.order:03d}.{extension}"
            with image.image.open("rb") as image_file:
                zip_file.writestr(filename, image_file.read())
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{folder_name}.zip")


def search(request):
    query = request.GET.get("q", "")
    results = []
    if query:
        results = Manga.objects.filter(
            Q(title__icontains=query)
            | Q(keywords__keyword__icontains=query)
            | Q(description__icontains=query)
        ).distinct()
    return render(request, "search.html", {"query": query, "results": results})


def search_suggest(request):
    query = request.GET.get("q", "")
    suggestions = []
    if query:
        title_matches = (
            Manga.objects.filter(title__istartswith=query)
            .values_list("title", flat=True)
            .distinct()[:10]
        )
        keyword_matches = (
            SearchKeyword.objects.filter(keyword__istartswith=query)
            .values_list("keyword", flat=True)
            .distinct()[:10]
        )
        suggestions = list(dict.fromkeys(list(title_matches) + list(keyword_matches)))[:10]
    return JsonResponse({"suggestions": suggestions})


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            display_name = form.cleaned_data.get("display_name")
            if display_name:
                user.profile.display_name = display_name
                user.profile.save(update_fields=["display_name"])
            login(request, user)
            return redirect("home")
    else:
        form = RegistrationForm()
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request, username=form.cleaned_data["username"], password=form.cleaned_data["password"]
            )
            if user:
                if _user_is_banned(user):
                    messages.error(request, "حسابك محظور.")
                    return redirect("login")
                login(request, user)
                return redirect("home")
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def profile(request):
    lists = ReadingListEntry.objects.filter(user=request.user).select_related("manga")
    return render(
        request,
        "profile.html",
        {"lists": lists, "device_id": request.COOKIES.get("device_id")},
    )


def forum(request):
    posts = ForumPost.objects.select_related("author").order_by("-created_at")
    if request.method == "POST" and request.user.is_authenticated:
        form = ForumPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("forum")
    else:
        form = ForumPostForm()
    return render(request, "forum.html", {"posts": posts, "form": form})


def forum_detail(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    replies = ForumReply.objects.filter(post=post).select_related("author").order_by("created_at")
    if request.method == "POST" and request.user.is_authenticated:
        form = ForumReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = post
            reply.author = request.user
            reply.save()
            return redirect("forum_detail", post_id=post_id)
    else:
        form = ForumReplyForm()
    return render(request, "forum_detail.html", {"post": post, "replies": replies, "form": form})


@login_required
def support(request):
    threads = SupportThread.objects.filter(user=request.user).order_by("-created_at")
    if request.method == "POST":
        form = SupportMessageForm(request.POST)
        if form.is_valid():
            thread_id = request.POST.get("thread_id")
            thread = None
            if thread_id:
                thread = get_object_or_404(SupportThread, id=thread_id, user=request.user)
            if not thread:
                thread = SupportThread.objects.create(user=request.user)
            if thread.status == "open":
                message = form.save(commit=False)
                message.thread = thread
                message.sender = request.user
                message.save()
            return redirect("support")
    else:
        form = SupportMessageForm()
    return render(request, "support.html", {"threads": threads, "form": form})


@login_required
def close_support(request, thread_id):
    thread = get_object_or_404(SupportThread, id=thread_id, user=request.user)
    thread.status = "closed"
    thread.closed_by = "user"
    thread.save(update_fields=["status", "closed_by"])
    return redirect("support")


@login_required
def inbox(request):
    threads = PrivateThread.objects.filter(Q(user_one=request.user) | Q(user_two=request.user))
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        if username:
            target = get_user_model().objects.filter(username=username).first()
            if target and target != request.user:
                user_one, user_two = sorted([request.user, target], key=lambda user: user.id)
                thread, _ = PrivateThread.objects.get_or_create(user_one=user_one, user_two=user_two)
                return redirect("thread_detail", thread_id=thread.id)
            messages.error(request, "المستخدم غير موجود.")
    return render(request, "inbox.html", {"threads": threads})


@login_required
def thread_detail(request, thread_id):
    thread = get_object_or_404(
        PrivateThread.objects.select_related("user_one", "user_two"), id=thread_id
    )
    if request.user not in [thread.user_one, thread.user_two]:
        return redirect("inbox")
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            PrivateMessage.objects.create(thread=thread, sender=request.user, content=content)
            return redirect("thread_detail", thread_id=thread_id)
    messages_list = thread.messages.select_related("sender").order_by("created_at")
    return render(
        request,
        "thread_detail.html",
        {"thread": thread, "messages": messages_list},
    )


def reader_settings(request):
    return render(request, "settings.html")
