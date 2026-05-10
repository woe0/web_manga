from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import (
    ChapterComment,
    ForumPost,
    ForumReply,
    MangaComment,
    Rating,
    SupportMessage,
)


class RegistrationForm(UserCreationForm):
    display_name = forms.CharField(label="الاسم الظاهر", max_length=120, required=False)

    class Meta:
        model = User
        fields = ("username", "display_name", "password1", "password2")


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="اسم المستخدم")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)


class MangaCommentForm(forms.ModelForm):
    class Meta:
        model = MangaComment
        fields = ("content", "is_spoiler", "parent")
        widgets = {"content": forms.Textarea(attrs={"rows": 3})}


class ChapterCommentForm(forms.ModelForm):
    class Meta:
        model = ChapterComment
        fields = ("content", "is_spoiler", "parent")
        widgets = {"content": forms.Textarea(attrs={"rows": 3})}


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ("value",)
        widgets = {
            "value": forms.Select(choices=[(i, i) for i in range(1, 6)]),
        }


class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ("content", "image")
        widgets = {"content": forms.Textarea(attrs={"rows": 3})}


class ForumReplyForm(forms.ModelForm):
    class Meta:
        model = ForumReply
        fields = ("content",)
        widgets = {"content": forms.Textarea(attrs={"rows": 2})}


class SupportMessageForm(forms.ModelForm):
    class Meta:
        model = SupportMessage
        fields = ("content",)
        widgets = {"content": forms.Textarea(attrs={"rows": 2})}
