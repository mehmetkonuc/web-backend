from django import forms
from .models import Post, PostImage

class PostForm(forms.ModelForm):
    """Form for creating and editing posts"""
    class Meta:
        model = Post
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ne düşünüyorsun?',
                'rows': 3,
                'maxlength': 280
            }),
        }
        labels = {
            'content': 'İçerik',
        }

# Multipart form - image uploads will be managed separately in the view