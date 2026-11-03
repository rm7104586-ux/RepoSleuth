import os
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib import messages
from django.db.models import Sum, Count
from django.conf import settings
from django.core.files import File

from analyzer.models import Project, ProjectAnalysis
from analyzer.forms import ProjectUploadForm
from analyzer.services.project_service import run_full_project_analysis
from analyzer.services.file_explorer import read_project_file_content
from analyzer.services.pdf_generator import generate_project_pdf_report
from analyzer.services.zip_extractor import ZipExtractionError


def dashboard_view(request):
    """
    Renders the modern developer dashboard.
    Displays aggregate stats, language distribution, and recent scans.
    """
    projects = Project.objects.all()
    total_projects = projects.count()
    completed_projects = projects.filter(status='completed')

    # Aggregated metrics
    agg = completed_projects.aggregate(
        total_files=Sum('total_files'),
        total_folders=Sum('total_folders'),
        total_loc=Sum('total_lines_of_code'),
    )

    # Compute total issues across all analyzed projects
    total_issues = 0
    all_analyses = ProjectAnalysis.objects.select_related('project').all()
    for analysis in all_analyses:
        total_issues += analysis.issue_counts.get('total', 0)

    # Aggregate language distribution
    global_languages = {}
    for proj in completed_projects:
        breakdown = proj.languages_breakdown or {}
        for lang, data in breakdown.items():
            if lang not in global_languages:
                global_languages[lang] = {'lines': 0, 'files': 0}
            global_languages[lang]['lines'] += data.get('lines', 0)
            global_languages[lang]['files'] += data.get('files', 0)

    # Prepare top languages for Chart.js
    sorted_langs = sorted(global_languages.items(), key=lambda x: x[1]['lines'], reverse=True)[:6]
    chart_labels = [k for k, _ in sorted_langs]
    chart_data = [v['lines'] for _, v in sorted_langs]

    # Recent scans (limit 8)
    recent_projects = projects[:8]

    context = {
        'total_projects': total_projects,
        'total_files': agg['total_files'] or 0,
        'total_folders': agg['total_folders'] or 0,
        'total_loc': agg['total_loc'] or 0,
        'total_issues': total_issues,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'recent_projects': recent_projects,
    }
    return render(request, 'analyzer/dashboard.html', context)


def project_upload_view(request):
    """Handles ZIP file upload, validation, and triggers analysis."""
    if request.method == 'POST':
        form = ProjectUploadForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            if not project.name:
                project.name = Path(project.uploaded_zip.name).stem.replace('_', ' ').title()
            project.status = 'pending'
            project.save()

            try:
                run_full_project_analysis(project)
                messages.success(request, f"Codebase '{project.name}' successfully analyzed!")
                return redirect('project_detail', project_id=project.id)
            except ZipExtractionError as ze:
                messages.error(request, f"Archive extraction failed: {str(ze)}")
                return redirect('project_upload')
            except Exception as e:
                messages.error(request, f"Analysis encountered an error: {str(e)}")
                return redirect('project_detail', project_id=project.id)
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field.title()}: {err}")
    else:
        form = ProjectUploadForm()

    return render(request, 'analyzer/upload.html', {'form': form})


def load_demo_project_view(request):
    """Creates and analyzes a sample demo project for instant preview."""
    demo_zip_path = Path(settings.BASE_DIR) / 'sample_projects' / 'demo_library_app.zip'

    if not demo_zip_path.exists():
        messages.error(request, "Demo project zip is missing. Please upload your own archive.")
        return redirect('project_upload')

    with open(demo_zip_path, 'rb') as f:
        project = Project(
            name="Demo Library Application",
            status='pending'
        )
        project.uploaded_zip.save('demo_library_app.zip', File(f), save=True)

    try:
        run_full_project_analysis(project)
        messages.success(request, "Demo project loaded and analyzed successfully!")
        return redirect('project_detail', project_id=project.id)
    except Exception as e:
        messages.error(request, f"Demo project analysis failed: {str(e)}")
        return redirect('dashboard')


def project_detail_view(request, project_id):
    """Overview dashboard for a specific project."""
    project = get_object_or_404(Project, id=project_id)
    analysis = getattr(project, 'analysis', None)

    # Prepare language data for Chart.js
    lang_labels = []
    lang_data = []
    if project.languages_breakdown:
        sorted_langs = sorted(
            project.languages_breakdown.items(),
            key=lambda x: x[1].get('lines', 0),
            reverse=True
        )
        for lang, stats in sorted_langs:
            lang_labels.append(lang)
            lang_data.append(stats.get('lines', 0))

    context = {
        'project': project,
        'analysis': analysis,
        'lang_labels': lang_labels,
        'lang_data': lang_data,
    }
    return render(request, 'analyzer/project_overview.html', context)


def file_explorer_view(request, project_id):
    """Interactive tree view file explorer."""
    project = get_object_or_404(Project, id=project_id)
    analysis = getattr(project, 'analysis', None)

    file_tree = analysis.file_tree if analysis else []

    context = {
        'project': project,
        'analysis': analysis,
        'file_tree': file_tree,
    }
    return render(request, 'analyzer/file_explorer.html', context)


def file_content_api_view(request, project_id):
    """JSON API endpoint to safely fetch file content for the code viewer modal."""
    project = get_object_or_404(Project, id=project_id)
    rel_path = request.GET.get('path', '').strip()

    if not rel_path or not project.extracted_path:
        return JsonResponse({'success': False, 'error': 'Invalid path or extracted files missing.'}, status=400)

    result = read_project_file_content(project.extracted_path, rel_path)
    return JsonResponse(result)


def dependency_analyzer_view(request, project_id):
    """Displays interactive dependency network and external libraries."""
    project = get_object_or_404(Project, id=project_id)
    analysis = getattr(project, 'analysis', None)

    if not analysis:
        messages.warning(request, "Analysis data not available for this project.")
        return redirect('project_detail', project_id=project.id)

    internal_deps = analysis.internal_dependencies or {}
    external_deps = analysis.external_dependencies or []

    context = {
        'project': project,
        'analysis': analysis,
        'nodes': internal_deps.get('nodes', []),
        'edges': internal_deps.get('edges', []),
        'confirmed_count': internal_deps.get('confirmed_count', 0),
        'estimated_count': internal_deps.get('estimated_count', 0),
        'total_dependencies': internal_deps.get('total_dependencies', 0),
        'external_dependencies': external_deps,
    }
    return render(request, 'analyzer/dependency_analyzer.html', context)


def entry_points_view(request, project_id):
    """Displays detected application starting points and explanations."""
    project = get_object_or_404(Project, id=project_id)
    analysis = getattr(project, 'analysis', None)

    entry_points = analysis.entry_points if analysis else []

    context = {
        'project': project,
        'analysis': analysis,
        'entry_points': entry_points,
    }
    return render(request, 'analyzer/entry_points.html', context)


def code_issues_view(request, project_id):
    """Displays detected issues: syntax errors, TODO/FIXME, empty files, large files."""
    project = get_object_or_404(Project, id=project_id)
    analysis = getattr(project, 'analysis', None)

    issues = analysis.issues if analysis else []
    counts = analysis.issue_counts if analysis else {}

    # Category filter
    category_filter = request.GET.get('category', 'all')
    severity_filter = request.GET.get('severity', 'all')

    filtered_issues = issues
    if category_filter != 'all':
        filtered_issues = [i for i in filtered_issues if i.get('category') == category_filter]
    if severity_filter != 'all':
        filtered_issues = [i for i in filtered_issues if i.get('severity') == severity_filter]

    context = {
        'project': project,
        'analysis': analysis,
        'issues': filtered_issues,
        'counts': counts,
        'active_category': category_filter,
        'active_severity': severity_filter,
    }
    return render(request, 'analyzer/code_issues.html', context)


def project_pdf_download_view(request, project_id):
    """Generates and streams the academic PDF analysis report."""
    project = get_object_or_404(Project, id=project_id)
    analysis = getattr(project, 'analysis', None)

    if not analysis:
        messages.error(request, "Analysis report cannot be generated because project analysis is incomplete.")
        return redirect('project_detail', project_id=project.id)

    try:
        pdf_bytes = generate_project_pdf_report(project, analysis)
        safe_filename = "".join(c for c in project.name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filename = f"RepoSleuth_Report_{safe_filename.replace(' ', '_')}.pdf"

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"Failed to generate PDF: {str(e)}")
        return redirect('project_detail', project_id=project.id)


def history_view(request):
    """Lists all scanned projects with stats and management controls."""
    projects = Project.objects.all()
    query = request.GET.get('q', '').strip()

    if query:
        projects = projects.filter(name__icontains=query)

    context = {
        'projects': projects,
        'query': query,
    }
    return render(request, 'analyzer/history.html', context)


def project_delete_view(request, project_id):
    """Deletes project record and purges files from storage."""
    project = get_object_or_404(Project, id=project_id)
    project_name = project.name

    if request.method == 'POST':
        project.delete()
        messages.success(request, f"Project '{project_name}' was permanently deleted.")
        return redirect('history')

    return render(request, 'analyzer/project_confirm_delete.html', {'project': project})
