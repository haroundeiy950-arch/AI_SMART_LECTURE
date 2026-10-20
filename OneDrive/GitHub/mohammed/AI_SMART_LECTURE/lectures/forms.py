from django import forms
from .models import Lecture, Question


class LectureForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = ['title', 'subject', 'description', 'privacy', 'video', 'audio', 'attachment', 'transcript', 'summary', 'notes']
        widgets = {k: forms.Textarea(attrs={'rows': 4}) for k in ['description', 'transcript', 'summary', 'notes']}


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Write a question…'})}
