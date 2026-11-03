import io
import os
import zipfile
import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from analyzer.models import Project, ProjectAnalysis
from analyzer.services.zip_extractor import safe_extract_zip, ZipExtractionError
from analyzer.services.file_explorer import build_file_tree_and_metrics, read_project_file_content
from analyzer.services.ast_analyzer import analyze_codebase_dependencies
from analyzer.services.entrypoint_detector import detect_entry_points
from analyzer.services.issue_detector import detect_code_issues
from analyzer.services.pdf_generator import generate_project_pdf_report
from analyzer.services.project_service import run_full_project_analysis


class RepoSleuthServicesTests(TestCase):
    def setUp(self):
        self.sample_zip_path = Path('sample_projects/demo_library_app.zip').resolve()

    def test_safe_zip_extraction(self):
        """Tests that a legitimate zip file extracts cleanly into destination."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = safe_extract_zip(str(self.sample_zip_path), tmp_dir)
            self.assertTrue(os.path.isdir(result['extracted_path']))
            self.assertGreater(result['file_count'], 0)

    def test_zip_invalid_file(self):
        """Tests that non-zip files are rejected."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"not a zip")
            invalid_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                with self.assertRaises(ZipExtractionError):
                    safe_extract_zip(invalid_path, tmp_dir)
        finally:
            if os.path.exists(invalid_path):
                os.remove(invalid_path)

    def test_file_explorer_metrics(self):
        """Tests file tree hierarchy and lines of code counting."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_result = safe_extract_zip(str(self.sample_zip_path), tmp_dir)
            metrics = build_file_tree_and_metrics(extract_result['extracted_path'])

            self.assertGreater(metrics['total_files'], 0)
            self.assertGreater(metrics['total_lines'], 0)
            self.assertIn('Python', metrics['languages'])
            self.assertGreater(len(metrics['python_files']), 0)

    def test_ast_dependency_analysis(self):
        """Tests AST import extraction and confirmed vs estimated classification."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_result = safe_extract_zip(str(self.sample_zip_path), tmp_dir)
            root = extract_result['extracted_path']
            metrics = build_file_tree_and_metrics(root)

            deps = analyze_codebase_dependencies(root, metrics['python_files'])

            self.assertGreaterEqual(deps['confirmed_count'], 1)
            # requests and flask should be in external dependencies
            ext_names = [d['package'] for d in deps['external_dependencies']]
            self.assertTrue('flask' in ext_names or 'requests' in ext_names)

    def test_entrypoint_detection(self):
        """Tests detection of app.py and main.py entry points with explanations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_result = safe_extract_zip(str(self.sample_zip_path), tmp_dir)
            root = extract_result['extracted_path']
            metrics = build_file_tree_and_metrics(root)

            entries = detect_entry_points(root, metrics['python_files'])
            detected_names = [e['filename'] for e in entries]

            self.assertIn('main.py', detected_names)
            self.assertIn('app.py', detected_names)

            for entry in entries:
                self.assertTrue(len(entry['reasons']) > 0)
                self.assertIn(entry['confidence'], ['High', 'Medium', 'Low'])

    def test_issue_detection(self):
        """Tests detection of syntax errors, TODO/FIXME comments, and empty files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_result = safe_extract_zip(str(self.sample_zip_path), tmp_dir)
            root = extract_result['extracted_path']
            metrics = build_file_tree_and_metrics(root)

            issues_result = detect_code_issues(root, metrics['python_files'])
            counts = issues_result['counts']

            # Must catch the intentional broken syntax in sample_broken_syntax.py
            self.assertGreaterEqual(counts['syntax_errors'], 1)
            # Must catch the TODO and FIXME comments
            self.assertGreaterEqual(counts['todos_fixmes'], 2)
            # Must catch the empty module
            self.assertGreaterEqual(counts['empty_files'], 1)
            # Health score calculated
            self.assertTrue(0 <= issues_result['health_score'] <= 100)

    def test_pdf_report_generation(self):
        """Tests ReportLab PDF document compilation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_result = safe_extract_zip(str(self.sample_zip_path), tmp_dir)
            root = extract_result['extracted_path']
            metrics = build_file_tree_and_metrics(root)
            deps = analyze_codebase_dependencies(root, metrics['python_files'])
            entries = detect_entry_points(root, metrics['python_files'])
            issues = detect_code_issues(root, metrics['python_files'])

            with open(self.sample_zip_path, 'rb') as f:
                uploaded = SimpleUploadedFile('demo_library_app.zip', f.read())

            project = Project.objects.create(
                name="Demo Library App",
                uploaded_zip=uploaded,
                extracted_path=root,
                status='completed',
                total_files=metrics['total_files'],
                total_folders=metrics['total_folders'],
                total_size_bytes=metrics['total_size'],
                total_lines_of_code=metrics['total_lines'],
                languages_breakdown=metrics['languages']
            )

            analysis = ProjectAnalysis.objects.create(
                project=project,
                entry_points=entries,
                internal_dependencies=deps,
                external_dependencies=deps['external_dependencies'],
                issues=issues['issues'],
                issue_counts=issues['counts'],
                file_tree=metrics['tree'],
                health_score=issues['health_score']
            )

            pdf_bytes = generate_project_pdf_report(project, analysis)
            self.assertIsInstance(pdf_bytes, bytes)
            self.assertGreater(len(pdf_bytes), 1000)
            # PDF header magic bytes
            self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_full_pipeline_run(self):
        """Tests full end-to-end service orchestration."""
        with open(self.sample_zip_path, 'rb') as f:
            uploaded = SimpleUploadedFile('pipeline_test.zip', f.read())

        project = Project.objects.create(
            name="Pipeline Test App",
            uploaded_zip=uploaded
        )

        analysis = run_full_project_analysis(project)
        project.refresh_from_db()

        self.assertEqual(project.status, 'completed')
        self.assertGreater(project.total_files, 0)
        self.assertGreater(len(analysis.entry_points), 0)
        self.assertGreater(analysis.issue_counts['total'], 0)


class RepoSleuthViewTests(TestCase):
    """Integration tests verifying all views, routes, and responses."""

    def setUp(self):
        sample_zip = Path('sample_projects/demo_library_app.zip').resolve()
        with open(sample_zip, 'rb') as f:
            uploaded = SimpleUploadedFile('demo_app.zip', f.read())

        self.project = Project.objects.create(
            name="Test Web Library",
            uploaded_zip=uploaded
        )
        self.analysis = run_full_project_analysis(self.project)
        self.project.refresh_from_db()

    def test_dashboard_view(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RepoSleuth")
        self.assertContains(response, "Test Web Library")

    def test_upload_get_view(self):
        response = self.client.get('/upload/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload Software Codebase")

    def test_project_detail_view(self):
        response = self.client.get(f'/project/{self.project.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Web Library")
        self.assertContains(response, "Investigation Modules")

    def test_file_explorer_view(self):
        response = self.client.get(f'/project/{self.project.id}/files/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Interactive File Explorer")

    def test_file_content_api(self):
        # Fetch app.py content
        response = self.client.get(f'/project/{self.project.id}/file-content/?path=app.py')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['file_name'], 'app.py')
        self.assertEqual(data['language'], 'Python')
        self.assertGreater(len(data['lines']), 0)

    def test_dependency_analyzer_view(self):
        response = self.client.get(f'/project/{self.project.id}/dependencies/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Module Dependency Analyzer")
        self.assertContains(response, "network-graph-container")

    def test_entry_points_view(self):
        response = self.client.get(f'/project/{self.project.id}/entry-points/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Entry Point Detector")
        self.assertContains(response, "main.py")
        self.assertContains(response, "app.py")

    def test_code_issues_view(self):
        response = self.client.get(f'/project/{self.project.id}/issues/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Code Issue & Smell Detector")
        self.assertContains(response, "Python Syntax Error")

    def test_project_pdf_view(self):
        response = self.client.get(f'/project/{self.project.id}/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_history_view(self):
        response = self.client.get('/history/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scanned Codebase History")
        self.assertContains(response, "Test Web Library")

    def test_project_delete_view(self):
        # Post to delete
        response = self.client.post(f'/project/{self.project.id}/delete/')
        self.assertEqual(response.status_code, 302)  # Redirects to history
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

