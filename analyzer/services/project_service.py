"""
Project Analysis Orchestration Service for RepoSleuth.
Coordinates ZIP extraction, metric counting, AST dependency mapping,
entry point detection, code issue detection, and database persistence.
"""

import os
from pathlib import Path
from django.conf import settings
from analyzer.models import Project, ProjectAnalysis
from analyzer.services.zip_extractor import safe_extract_zip, ZipExtractionError
from analyzer.services.file_explorer import build_file_tree_and_metrics
from analyzer.services.ast_analyzer import analyze_codebase_dependencies
from analyzer.services.entrypoint_detector import detect_entry_points
from analyzer.services.issue_detector import detect_code_issues


def run_full_project_analysis(project: Project) -> ProjectAnalysis:
    """
    Executes complete static analysis pipeline on an uploaded Project.

    1. Safely extracts project ZIP.
    2. Builds file tree, LOC, and language metrics.
    3. Runs Python AST dependency analysis.
    4. Detects application entry points with explanations.
    5. Detects code issues, syntax errors, and code smells.
    6. Persists analysis to database.
    """
    project.status = 'analyzing'
    project.save(update_fields=['status'])

    destination_dir = Path(settings.MEDIA_ROOT) / 'extracted' / f"project_{project.id}"

    try:
        # Step 1: Safe ZIP Extraction
        zip_path = project.uploaded_zip.path
        extract_result = safe_extract_zip(zip_path, str(destination_dir))
        extracted_root = extract_result['extracted_path']

        project.extracted_path = extracted_root

        # Step 2: File Explorer & Codebase Metrics
        file_metrics = build_file_tree_and_metrics(extracted_root)
        project.total_files = file_metrics['total_files']
        project.total_folders = file_metrics['total_folders']
        project.total_size_bytes = file_metrics['total_size']
        project.total_lines_of_code = file_metrics['total_lines']
        project.languages_breakdown = file_metrics['languages']

        python_files = file_metrics['python_files']

        # Step 3: AST Dependency Analysis
        dep_results = analyze_codebase_dependencies(extracted_root, python_files)

        # Step 4: Entry Point Detection
        entry_points = detect_entry_points(extracted_root, python_files)

        # Step 5: Code Issues & Smells
        issue_results = detect_code_issues(extracted_root, python_files)

        # Step 6: Create or Update ProjectAnalysis
        analysis, _ = ProjectAnalysis.objects.update_or_create(
            project=project,
            defaults={
                'entry_points': entry_points,
                'internal_dependencies': {
                    'nodes': dep_results['nodes'],
                    'edges': dep_results['edges'],
                    'confirmed_count': dep_results['confirmed_count'],
                    'estimated_count': dep_results['estimated_count'],
                    'total_dependencies': dep_results['total_dependencies'],
                },
                'external_dependencies': dep_results['external_dependencies'],
                'issues': issue_results['issues'],
                'issue_counts': issue_results['counts'],
                'file_tree': file_metrics['tree'],
                'health_score': issue_results['health_score']
            }
        )

        project.status = 'completed'
        project.error_message = ''
        project.save()

        return analysis

    except ZipExtractionError as ze:
        project.status = 'failed'
        project.error_message = f"Archive Error: {str(ze)}"
        project.save()
        raise
    except Exception as e:
        project.status = 'failed'
        project.error_message = f"Analysis Failed: {str(e)}"
        project.save()
        raise
