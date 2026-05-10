from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("manga/<slug:slug>/", views.manga_detail, name="manga_detail"),
    path("manga/<slug:slug>/comment/", views.add_manga_comment, name="add_manga_comment"),
    path(
        "manga/comment/<int:comment_id>/react/",
        views.react_manga_comment,
        name="react_manga_comment",
    ),
    path("manga/<slug:slug>/rate/", views.add_rating, name="add_rating"),
    path("manga/<slug:slug>/list/", views.add_to_list, name="add_to_list"),
    path("chapter/<int:chapter_id>/", views.chapter_reader, name="chapter_reader"),
    path(
        "chapter/<int:chapter_id>/comment/",
        views.add_chapter_comment,
        name="add_chapter_comment",
    ),
    path(
        "chapter/comment/<int:comment_id>/react/",
        views.react_chapter_comment,
        name="react_chapter_comment",
    ),
    path(
        "chapter/<int:chapter_id>/toggle-read/",
        views.toggle_chapter_read,
        name="toggle_chapter_read",
    ),
    path(
        "chapter/<int:chapter_id>/download/",
        views.download_chapter,
        name="download_chapter",
    ),
    path("search/", views.search, name="search"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("forum/", views.forum, name="forum"),
    path("forum/<int:post_id>/", views.forum_detail, name="forum_detail"),
    path("support/", views.support, name="support"),
    path("support/<int:thread_id>/close/", views.close_support, name="close_support"),
    path("inbox/", views.inbox, name="inbox"),
    path("threads/<int:thread_id>/", views.thread_detail, name="thread_detail"),
    path("settings/", views.reader_settings, name="reader_settings"),
]
