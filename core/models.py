from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.text import slugify

User = get_user_model()


class Profile(models.Model):
    THEME_CHOICES = [
        ("light", "نهاري"),
        ("dark", "ليلي"),
    ]
    READER_CHOICES = [
        ("vertical", "عمودي"),
        ("webtoon", "ويب تون"),
        ("horizontal", "أفقي"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    banned = models.BooleanField(default=False)
    reader_mode = models.CharField(max_length=20, choices=READER_CHOICES, default="vertical")
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="light")
    merge_pages = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.display_name or self.user.username


class BannedDevice(models.Model):
    identifier = models.CharField(max_length=64, unique=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.identifier


class Category(models.Model):
    CATEGORY_TYPES = [
        ("genre", "تصنيف"),
        ("age", "تصنيف عمري"),
    ]

    name = models.CharField(max_length=120, unique=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default="genre")

    def __str__(self) -> str:
        return self.name


def manga_cover_path(instance: "Manga", filename: str) -> str:
    slug = instance.slug or slugify(instance.title)
    return f"covers/{slug}/{filename}"


class Manga(models.Model):
    MANGA_TYPES = [
        ("manga", "مانجا"),
        ("manhwa", "مانهوا"),
        ("manhua", "مانها"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to=manga_cover_path, blank=True, null=True)
    manga_type = models.CharField(max_length=20, choices=MANGA_TYPES, default="manga")
    categories = models.ManyToManyField(Category, blank=True, related_name="manga")
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class SearchKeyword(models.Model):
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name="keywords")
    keyword = models.CharField(max_length=120, db_index=True)

    def __str__(self) -> str:
        return self.keyword


class Chapter(models.Model):
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name="chapters")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("manga", "number")
        ordering = ["number"]

    def __str__(self) -> str:
        return f"{self.manga.title} - {self.number}"


def chapter_image_path(instance: "ChapterImage", filename: str) -> str:
    return f"chapters/{instance.chapter.manga_id}/{instance.chapter.number}/{filename}"


class ChapterImage(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=chapter_image_path)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.chapter} - {self.order}"


class Rating(models.Model):
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    value = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("manga", "user")

    def __str__(self) -> str:
        return f"{self.manga} - {self.value}"


class ReadingListEntry(models.Model):
    LIST_TYPES = [
        ("wish", "أرغب بمشاهدتها"),
        ("later", "أشاهدها لاحقاً"),
        ("reading", "أشاهدها حالياً"),
        ("completed", "تم مشاهدتها"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reading_entries")
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name="reading_entries")
    list_type = models.CharField(max_length=20, choices=LIST_TYPES)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "manga", "list_type")


class ChapterRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chapter_reads")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="read_marks")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "chapter")


class MangaComment(models.Model):
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="manga_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.TextField()
    is_spoiler = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class MangaCommentReaction(models.Model):
    comment = models.ForeignKey(MangaComment, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="manga_comment_reactions")
    is_like = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comment", "user")


class ChapterComment(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chapter_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.TextField()
    is_spoiler = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ChapterCommentReaction(models.Model):
    comment = models.ForeignKey(ChapterComment, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chapter_comment_reactions")
    is_like = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comment", "user")


class ForumPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_posts")
    content = models.TextField()
    image = models.ImageField(upload_to="forum/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"منشور {self.author}"


class ForumReply(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_replies")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class PrivateThread(models.Model):
    user_one = models.ForeignKey(User, on_delete=models.CASCADE, related_name="threads_started")
    user_two = models.ForeignKey(User, on_delete=models.CASCADE, related_name="threads_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user_one", "user_two")


class PrivateMessage(models.Model):
    thread = models.ForeignKey(PrivateThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="private_messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class SupportThread(models.Model):
    STATUS_CHOICES = [
        ("open", "مفتوح"),
        ("closed", "مغلق"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_threads")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    closed_by = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SupportMessage(models.Model):
    thread = models.ForeignKey(SupportThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_messages")
    is_admin = models.BooleanField(default=False)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class LastViewed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="last_viewed")
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name="last_viewed")
    last_viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "manga")


class DeviceSession(models.Model):
    identifier = models.UUIDField(default=uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
