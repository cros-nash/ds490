""" maps app's url patterns to views. 
make sure to update project url file at frontend/urls.py 
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='scraper/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('api-key/', views.api_key, name='api_key'),
    path('projects/new/', views.create_project, name='create_project'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.edit_project, name='edit_project'),
    path('projects/<int:pk>/delete/', views.delete_project, name='delete_project'),
    path('projects/<int:pk>/generate/', views.generate_script, name='generate_script'),
    path('field-specification/add/', views.add_field_specification, name='add_field_specification'),
    path('execution/<int:result_id>/', views.execution_status, name='execution_status'),
    path('results/<int:result_id>/', views.results_screen, name='results_screen'),
    path('api/logs/<int:result_id>/', views.get_logs, name='get_logs'),
    path('download/<int:result_id>/', views.download_container, name='download_container'),
]