import io
import zipfile
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Max, Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    ChapterCommentForm,
    ForumPostForm,
    ForumReplyForm,
    LoginForm,
    MangaCommentForm,
    ProfileForm,
    RatingForm,
    RegistrationForm,
    SupportMessageForm,
)
from .models import (
    Category,
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
    return bool(profile and profile.banned)


def _annotate_latest_chapter(qs):
    return qs.annotate(latest_chapter=Max("chapters__number"))


def home(request):
    popular = _annotate_latest_chapter(Manga.objects.order_by("-view_count"))[:6]
    latest = _annotate_latest_chapter(Manga.objects.order_by("-created_at"))[:12]
    manhwa = _annotate_latest_chapter(
        Manga.objects.filter(manga_type="manhwa").order_by("-created_at")
    )[:8]
    manhua = _annotate_latest_chapter(
        Manga.objects.filter(manga_type="manhua").order_by("-created_at")
    )[:8]
    manga = _annotate_latest_chapter(
        Manga.objects.filter(manga_type="manga").order_by("-created_at")
    )[:8]

    last_viewed = []
    if request.user.is_authenticated:
        last_viewed_entries = (
            LastViewed.objects.filter(user=request.user)
            .select_related("manga")
            .order_by("-last_viewed_at")[:6]
        )
        last_viewed = [entry.manga for entry in last_viewed_entries if entry.manga]
    else:
        viewed_ids = request.session.get("last_viewed", [])
        if viewed_ids:
            mapping = {m.id: m for m in Manga.objects.filter(id__in=viewed_ids)}
            last_viewed = [mapping[i] for i in viewed_ids if i in mapping]

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
            "categories": Category.objects.filter(category_type="genre")[:20],
        },
    )


def browse(request):
    qs = Manga.objects.all()
    manga_type = request.GET.get("type")
    category_id = request.GET.get("category")
    sort = request.GET.get("sort", "latest")

    if manga_type in {"manga", "manhwa", "manhua"}:
        qs = qs.filter(manga_type=manga_type)
    if category_id:
        qs = qs.filter(categories__id=category_id)

    if sort == "popular":
        qs = qs.order_by("-view_count")
    elif sort == "rating":
        qs = qs.annotate(_avg=Avg("ratings__value")).order_by("-_avg", "-view_count")
    elif sort == "name":
        qs = qs.order_by("title")
    else:
        qs = qs.order_by("-created_at")

    qs = _annotate_latest_chapter(qs.distinct())
    return render(
        request,
        "browse.html",
        {
            "results": qs,
            "categories": Category.objects.filter(category_type="genre"),
            "age_categories": Category.objects.filter(category_type="age"),
            "current_type": manga_type or "",
            "current_category": int(category_id) if category_id and category_id.isdigit() else None,
            "current_sort": sort,
        },
    )


def manga_detail(request, slug):
    manga = get_object_or_404(Manga.objects.prefetch_related("categories"), slug=slug)
    order = request.GET.get("order", "asc")
    chapters = manga.chapters.all().order_by("-number" if order == "desc" else "number")
    new_threshold = timezone.now() - timedelta(days=3)
    new_chapter_ids = set(
        manga.chapters.filter(published_at__gte=new_threshold).values_list("id", flat=True)
    )
    rating_average = manga.ratings.aggregate(avg=Avg("value"))["avg"]
    rating_count = manga.ratings.count()
    chapter_comment_counts = dict(
        ChapterComment.objects.filter(chapter__manga=manga)
        .values("chapter_id")
        .annotate(c=Count("id"))
        .values_list("chapter_id", "c")
    )

    manga_comments = (
        MangaComment.objects.filter(manga=manga, parent__isnull=True)
        .annotate(
            likes_count=Count("reactions", filter=Q(reactions__is_like=True), distinct=True),
            dislikes_count=Count("reactions", filter=Q(reactions__is_like=False), distinct=True),
            replies_count=Count("replies", distinct=True),
        )
        .select_related("user", "user__profile")
        .prefetch_related("replies__user__profile")
        .order_by("-created_at")
    )
    chapter_reads = set()
    user_list_type = None
    user_rating = None
    if request.user.is_authenticated:
        chapter_reads = set(
            ChapterRead.objects.filter(user=request.user, chapter__manga=manga).values_list(
                "chapter_id", flat=True
            )
        )
        entry = ReadingListEntry.objects.filter(user=request.user, manga=manga).first()
        if entry:
            user_list_type = entry.list_type
        rating_obj = Rating.objects.filter(user=request.user, manga=manga).first()
        if rating_obj:
            user_rating = rating_obj.value
    return render(
        request,
        "manga_detail.html",
        {
            "manga": manga,
            "chapters": chapters,
            "order": order,
            "new_chapter_ids": new_chapter_ids,
            "rating_average": rating_average,
            "rating_count": rating_count,
            "manga_comments": manga_comments,
            "comment_form": MangaCommentForm(),
            "rating_form": RatingForm(initial={"value": user_rating} if user_rating else None),
            "chapter_reads": chapter_reads,
            "chapter_comment_counts": chapter_comment_counts,
            "user_list_type": user_list_type,
            "user_rating": user_rating,
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
    existing = MangaCommentReaction.objects.filter(comment=comment, user=request.user).first()
    if existing and existing.is_like == is_like:
        existing.delete()
    else:
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
    existing = ChapterCommentReaction.objects.filter(comment=comment, user=request.user).first()
    if existing and existing.is_like == is_like:
        existing.delete()
    else:
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
    valid_types = {"wish", "later", "reading", "completed"}
    if list_type == "remove":
        ReadingListEntry.objects.filter(user=request.user, manga=manga).delete()
        messages.success(request, "تمت الإزالة من القائمة.")
    elif list_type in valid_types:
        ReadingListEntry.objects.filter(user=request.user, manga=manga).delete()
        ReadingListEntry.objects.create(user=request.user, manga=manga, list_type=list_type)
        messages.success(request, "تمت الإضافة إلى القائمة.")
    return redirect("manga_detail", slug=slug)


@login_required
def toggle_chapter_read(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    mark = ChapterRead.objects.filter(user=request.user, chapter=chapter)
    if mark.exists():
        mark.delete()
        return JsonResponse({"success": True, "read": False})
    ChapterRead.objects.create(user=request.user, chapter=chapter)
    return JsonResponse({"success": True, "read": True})


def chapter_reader(request, chapter_id):
    chapter = get_object_or_404(Chapter.objects.select_related("manga"), id=chapter_id)
    chapter.view_count += 1
    chapter.save(update_fields=["view_count"])
    Manga.objects.filter(id=chapter.manga_id).update(view_count=F("view_count") + 1)
    if request.user.is_authenticated:
        LastViewed.objects.update_or_create(user=request.user, manga=chapter.manga)
        ChapterRead.objects.get_or_create(user=request.user, chapter=chapter)
    else:
        viewed = request.session.get("last_viewed", [])
        viewed = [v for v in viewed if v != chapter.manga_id]
        viewed.insert(0, chapter.manga_id)
        request.session["last_viewed"] = viewed[:10]

    siblings = list(chapter.manga.chapters.order_by("number").values("id", "number"))
    prev_chap = next_chap = None
    for i, c in enumerate(siblings):
        if c["id"] == chapter.id:
            if i > 0:
                prev_chap = siblings[i - 1]
            if i < len(siblings) - 1:
                next_chap = siblings[i + 1]
            break

    comments = (
        ChapterComment.objects.filter(chapter=chapter, parent__isnull=True)
        .annotate(
            likes_count=Count("reactions", filter=Q(reactions__is_like=True), distinct=True),
            dislikes_count=Count("reactions", filter=Q(reactions__is_like=False), distinct=True),
            replies_count=Count("replies", distinct=True),
        )
        .select_related("user", "user__profile")
        .prefetch_related("replies__user__profile")
        .order_by("-created_at")
    )
    return render(
        request,
        "chapter_reader.html",
        {
            "chapter": chapter,
            "images": chapter.images.all(),
            "comments": comments,
            "comment_form": ChapterCommentForm(),
            "prev_chap": prev_chap,
            "next_chap": next_chap,
        },
    )


def download_chapter(request, chapter_id):
    chapter = get_object_or_404(Chapter.objects.select_related("manga"), id=chapter_id)
    folder_name = f"{chapter.manga.title}، الفصل {chapter.number}"
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
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        results = (
            Manga.objects.filter(
                Q(title__icontains=query)
                | Q(keywords__keyword__icontains=query)
                | Q(description__icontains=query)
            )
            .distinct()
            .annotate(latest_chapter=Max("chapters__number"))
        )
    return render(request, "search.html", {"query": query, "results": results})


def search_suggest(request):
    query = request.GET.get("q", "").strip()
    suggestions = []
    if query:
        title_matches = list(
            Manga.objects.filter(Q(title__icontains=query) | Q(keywords__keyword__icontains=query))
            .distinct()
            .values("title", "slug")[:8]
        )
        seen = set()
        for m in title_matches:
            if m["title"] in seen:
                continue
            seen.add(m["title"])
            suggestions.append({"title": m["title"], "url": reverse("manga_detail", args=[m["slug"]])})
        keyword_matches = (
            SearchKeyword.objects.filter(keyword__icontains=query)
            .values_list("keyword", flat=True)
            .distinct()[:5]
        )
        for kw in keyword_matches:
            if kw not in seen:
                suggestions.append({"title": kw})
                seen.add(kw)
    return JsonResponse({"suggestions": suggestions[:10]})


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
            messages.success(request, "أهلاً بك في نوادر!")
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
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
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
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "تم حفظ التغييرات.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user.profile)

    lists = (
        ReadingListEntry.objects.filter(user=request.user)
        .select_related("manga")
        .order_by("-added_at")
    )
    return render(
        request,
        "profile.html",
        {
            "form": form,
            "lists": lists,
            "profile_obj": request.user.profile,
        },
    )


def forum(request):
    posts = (
        ForumPost.objects.select_related("author", "author__profile")
        .annotate(reply_count=Count("replies"))
        .order_by("-created_at")
    )
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
    post = get_object_or_404(
        ForumPost.objects.select_related("author", "author__profile"), id=post_id
    )
    replies = (
        ForumReply.objects.filter(post=post)
        .select_related("author", "author__profile")
        .order_by("created_at")
    )
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
    threads = (
        SupportThread.objects.filter(user=request.user)
        .prefetch_related("messages")
        .order_by("-created_at")
    )
    if request.method == "POST":
        form = SupportMessageForm(request.POST)
        if form.is_valid():
            thread_id = request.POST.get("thread_id")
            thread = None
            if thread_id:
                thread = SupportThread.objects.filter(id=thread_id, user=request.user).first()
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
    threads = (
        PrivateThread.objects.filter(Q(user_one=request.user) | Q(user_two=request.user))
        .select_related("user_one__profile", "user_two__profile")
        .order_by("-created_at")
    )
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
        PrivateThread.objects.select_related("user_one__profile", "user_two__profile"),
        id=thread_id,
    )
    if request.user not in [thread.user_one, thread.user_two]:
        return redirect("inbox")
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            PrivateMessage.objects.create(thread=thread, sender=request.user, content=content)
            return redirect("thread_detail", thread_id=thread_id)
    messages_list = thread.messages.select_related("sender", "sender__profile").order_by(
        "created_at"
    )
    other = thread.user_two if thread.user_one == request.user else thread.user_one
    return render(
        request,
        "thread_detail.html",
        {"thread": thread, "messages_list": messages_list, "other": other},
    )


def reader_settings(request):
    return render(request, "settings.html")
