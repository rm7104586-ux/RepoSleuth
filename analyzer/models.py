import os
import shutil
from pathlib import Path
from django.db import models


class Project(models.Model):
    """Represents an uploaded and analyzed software codebase project."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('analyzing', 'Analyzing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=255)
    uploaded_zip = models.FileField(upload_to='uploads/')
    extracted_path = models.CharField(max_length=1024, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')

    # Aggregate Metrics
    total_files = models.IntegerField(default=0)
    total_folders = models.IntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    total_lines_of_code = models.IntegerField(default=0)
    languages_breakdown = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def formatted_size(self):
        """Returns human-readable file size."""
        bytes_val = self.total_size_bytes
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        else:
            return f"{bytes_val / (1024 * 1024):.2f} MB"

    def delete(self, *args, **kwargs):
        """Safely remove uploaded zip and extracted directory upon model deletion."""
        # Remove uploaded zip file
        if self.uploaded_zip and os.path.isfile(self.uploaded_zip.path):
            try:
                os.remove(self.uploaded_zip.path)
            except OSError:
                pass

        # Remove extracted codebase directory
        if self.extracted_path and os.path.isdir(self.extracted_path):
            try:
                shutil.rmtree(self.extracted_path, ignore_errors=True)
            except OSError:
                pass

        super().delete(*args, **kwargs)


class ProjectAnalysis(models.Model):
    """Detailed static analysis results for a project."""

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='analysis')
    analyzed_at = models.DateTimeField(auto_now_add=True)

    # Detailed Results
    entry_points = models.JSONField(default=list, blank=True)
    internal_dependencies = models.JSONField(default=dict, blank=True)
    external_dependencies = models.JSONField(default=list, blank=True)
    issues = models.JSONField(default=list, blank=True)
    issue_counts = models.JSONField(default=dict, blank=True)
    file_tree = models.JSONField(default=list, blank=True)
    health_score = models.IntegerField(default=100)

    def __str__(self):
        return f"Analysis for {self.project.name}"
