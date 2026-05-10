from django.contrib import admin

from .models import (
    BannedDevice,
    Category,
    Chapter,
    ChapterComment,
    ChapterCommentReaction,
    ChapterImage,
    ChapterRead,
    DeviceSession,
    ForumPost,
    ForumReply,
    LastViewed,
    Manga,
    MangaComment,
    MangaCommentReaction,
    Profile,
    PrivateMessage,
    PrivateThread,
    Rating,
    ReadingListEntry,
    SearchKeyword,
    SupportMessage,
    SupportThread,
)

admin.site.site_header = "لوحة تحكم نوادر"
admin.site.site_title = "نوادر"
admin.site.index_title = "إدارة المحتوى"


@admin.register(Manga)
class MangaAdmin(admin.ModelAdmin):
    list_display = ("title", "manga_type", "view_count", "created_at")
    search_fields = ("title",)
    list_filter = ("manga_type", "created_at")


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("manga", "number", "title", "view_count", "published_at")
    list_filter = ("manga",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_type")
    list_filter = ("category_type",)


@admin.register(SearchKeyword)
class SearchKeywordAdmin(admin.ModelAdmin):
    list_display = ("keyword", "manga")
    search_fields = ("keyword", "manga__title")


admin.site.register(Profile)
admin.site.register(ChapterImage)
admin.site.register(MangaComment)
admin.site.register(MangaCommentReaction)
admin.site.register(ChapterComment)
admin.site.register(ChapterCommentReaction)
admin.site.register(ReadingListEntry)
admin.site.register(Rating)
admin.site.register(ChapterRead)
admin.site.register(ForumPost)
admin.site.register(ForumReply)
admin.site.register(PrivateThread)
admin.site.register(PrivateMessage)
admin.site.register(SupportThread)
admin.site.register(SupportMessage)
admin.site.register(BannedDevice)
admin.site.register(DeviceSession)
admin.site.register(LastViewed)
