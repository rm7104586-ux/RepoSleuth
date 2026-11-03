from django import forms
from analyzer.models import Project


class ProjectUploadForm(forms.ModelForm):
    """Form for uploading codebase ZIP files."""

    name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Custom project name (leave blank to use filename)'
        })
    )

    uploaded_zip = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.zip'
        })
    )

    class Meta:
        model = Project
        fields = ['name', 'uploaded_zip']

    def clean_uploaded_zip(self):
        zip_file = self.cleaned_data.get('uploaded_zip')
        if not zip_file:
            raise forms.ValidationError("Please select a ZIP file to upload.")

        filename = zip_file.name.lower()
        if not filename.endswith('.zip'):
            raise forms.ValidationError("Invalid file extension. Only .zip archives are supported.")

        # Max upload size 50MB
        if zip_file.size > 50 * 1024 * 1024:
            raise forms.ValidationError("Uploaded file exceeds 50MB limit.")

        return zip_file
