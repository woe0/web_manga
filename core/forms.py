from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import (
    ChapterComment,
    ForumPost,
    ForumReply,
    MangaComment,
    Profile,
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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("display_name", "avatar", "bio", "reader_mode", "theme", "merge_pages")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3, "placeholder": "نبذة قصيرة عنك..."}),
            "display_name": forms.TextInput(attrs={"placeholder": "الاسم الظاهر"}),
        }
        labels = {
            "display_name": "الاسم الظاهر",
            "avatar": "الصورة الشخصية",
            "bio": "النبذة",
            "reader_mode": "وضع القراءة الافتراضي",
            "theme": "المظهر",
            "merge_pages": "دمج الصفحات تلقائياً",
        }


class MangaCommentForm(forms.ModelForm):
    class Meta:
        model = MangaComment
        fields = ("content", "is_spoiler", "parent")
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3, "placeholder": "اكتب تعليقك..."}),
            "parent": forms.HiddenInput(),
        }


class ChapterCommentForm(forms.ModelForm):
    class Meta:
        model = ChapterComment
        fields = ("content", "is_spoiler", "parent")
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3, "placeholder": "اكتب تعليقك..."}),
            "parent": forms.HiddenInput(),
        }


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ("value",)
        widgets = {
            "value": forms.Select(choices=[(i, f"{i} نجوم") for i in range(1, 6)]),
        }


class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ("content", "image")
        widgets = {"content": forms.Textarea(attrs={"rows": 3, "placeholder": "شارك أفكارك..."})}


class ForumReplyForm(forms.ModelForm):
    class Meta:
        model = ForumReply
        fields = ("content",)
        widgets = {"content": forms.Textarea(attrs={"rows": 2, "placeholder": "اكتب رداً..."})}


class SupportMessageForm(forms.ModelForm):
    class Meta:
        model = SupportMessage
        fields = ("content",)
        widgets = {"content": forms.Textarea(attrs={"rows": 3, "placeholder": "كيف نستطيع مساعدتك؟"})}
