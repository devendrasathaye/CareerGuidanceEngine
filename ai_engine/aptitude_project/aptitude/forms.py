from django import forms

class UploadForm(forms.Form):
    video_file = forms.FileField(required=True)
    pdf_file = forms.FileField(required=True)

class AptitudeTestForm(forms.Form):
    video_file = forms.FileField(required=True)
    pdf_file = forms.FileField(required=True)
    name = forms.CharField(max_length=255)
    email = forms.EmailField(max_length=255)