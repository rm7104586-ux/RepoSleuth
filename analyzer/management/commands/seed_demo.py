from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from analyzer.models import Project
from analyzer.services.project_service import run_full_project_analysis


class Command(BaseCommand):
    help = "Loads and analyzes the pre-packaged demo project if not already present"

    def handle(self, *args, **options):
        if Project.objects.filter(name="Demo Library Application").exists():
            self.stdout.write(self.style.SUCCESS("Demo project already exists in database."))
            return

        demo_zip = Path(settings.BASE_DIR) / 'sample_projects' / 'demo_library_app.zip'
        if not demo_zip.exists():
            self.stdout.write(self.style.ERROR(f"Demo zip not found at {demo_zip}"))
            return

        with open(demo_zip, 'rb') as f:
            project = Project(
                name="Demo Library Application",
                status='pending'
            )
            project.uploaded_zip.save('demo_library_app.zip', File(f), save=True)

        try:
            analysis = run_full_project_analysis(project)
            self.stdout.write(self.style.SUCCESS(
                f"Successfully seeded demo project (ID: {project.id}): "
                f"{project.total_files} files, {project.total_lines_of_code} LOC, "
                f"{len(analysis.entry_points)} entry points, {analysis.issue_counts.get('total', 0)} issues."
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to seed demo project: {str(e)}"))
