from django.urls import path
from analyzer import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('upload/', views.project_upload_view, name='project_upload'),
    path('load-demo/', views.load_demo_project_view, name='load_demo'),
    path('history/', views.history_view, name='history'),

    # Individual Project Views
    path('project/<int:project_id>/', views.project_detail_view, name='project_detail'),
    path('project/<int:project_id>/files/', views.file_explorer_view, name='file_explorer'),
    path('project/<int:project_id>/file-content/', views.file_content_api_view, name='file_content_api'),
    path('project/<int:project_id>/dependencies/', views.dependency_analyzer_view, name='dependency_analyzer'),
    path('project/<int:project_id>/entry-points/', views.entry_points_view, name='entry_points'),
    path('project/<int:project_id>/issues/', views.code_issues_view, name='code_issues'),
    path('project/<int:project_id>/pdf/', views.project_pdf_download_view, name='project_pdf'),
    path('project/<int:project_id>/delete/', views.project_delete_view, name='project_delete'),
]
