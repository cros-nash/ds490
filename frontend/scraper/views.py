""" 
views = functions that process http requests and return responses
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .models import Project, ScrapingResult, APIKey, FieldSpecification
from .forms import ProjectForm, APIKeyForm, CustomUserCreationForm, FieldSpecificationForm
import json
import os
import tempfile
import importlib.util
import subprocess
import threading
import time
import sys

# Import local modules
from .script_generator import generate_script as generate_script_with_llm

def load_containerizer():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    module_path = os.path.join(project_root, 'containerizer.py')
    
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Could not find containerizer.py at {module_path}")
    
    spec = importlib.util.spec_from_file_location("containerizer", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module.Containerizer

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'scraper/signup.html', {'form': form})

@login_required
def api_key(request):
    try:
        api_key = APIKey.objects.get(user=request.user)
        form = APIKeyForm(instance=api_key)
    except APIKey.DoesNotExist:
        api_key = None
        form = APIKeyForm()
        
    if request.method == 'POST':
        if api_key:
            form = APIKeyForm(request.POST, instance=api_key)
        else:
            form = APIKeyForm(request.POST)
            
        if form.is_valid():
            api_key = form.save(commit=False)
            api_key.user = request.user
            api_key.save()
            messages.success(request, 'API key saved successfully.')
            return redirect('home')
            
    return render(request, 'scraper/api_key.html', {'form': form})

@login_required
def home(request):
    projects = Project.objects.filter(user=request.user)
    try:
        api_key = APIKey.objects.get(user=request.user)
    except APIKey.DoesNotExist:
        api_key = None
        
    return render(request, 'scraper/home.html', {
        'projects': projects,
        'has_api_key': api_key is not None
    })

@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            field_names = request.POST.getlist('field_name')
            field_types = request.POST.getlist('field_type')
            field_descriptions = request.POST.getlist('field_description')
            for i in range(len(field_names)):
                if field_names[i].strip():  # Only create if field name is not empty
                    FieldSpecification.objects.create(
                        project=project,
                        field_name=field_names[i],
                        field_type=field_types[i],
                        description=field_descriptions[i],
                        order=i
                    )
            messages.success(request, f'Project "{project.name}" created successfully.')
            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm()
        field_form = FieldSpecificationForm()
    return render(request, 'scraper/create_project.html', {
        'form': form,
        'field_form': field_form
        })

@login_required
def edit_project(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    field_specifications = project.field_specifications.all()

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            project.field_specifications.all().delete()
            field_names = request.POST.getlist('field_name')
            field_types = request.POST.getlist('field_type')
            field_descriptions = request.POST.getlist('field_description')
            for i in range(len(field_names)):
                if field_names[i].strip():  # Only create if field name is not empty
                    FieldSpecification.objects.create(
                        project=project,
                        field_name=field_names[i],
                        field_type=field_types[i],
                        description=field_descriptions[i],
                        order=i
                    )
            messages.success(request, f'Project "{project.name}" updated successfully.')
            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm(instance=project)
        
    return render(request, 'scraper/edit_project.html', {
        'form': form, 
        'project': project,
        'field_specifications': field_specifications
        })

@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Project "{project_name}" deleted successfully.')
        return redirect('home')
        
    return render(request, 'scraper/delete_project.html', {'project': project})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    results = ScrapingResult.objects.filter(project=project).order_by('-created_at')
    field_specifications = project.field_specifications.all()

    return render(request, 'scraper/project_detail.html', {
        'project': project,
        'results': results,
        'field_specifications': field_specifications
    })

@login_required
def add_field_specification(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        field_form = FieldSpecificationForm(data)
        if field_form.is_valid():
            # We don't save it here, just return the HTML for a new empty row
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': field_form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def generate_script(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    
    try:
        api_key = APIKey.objects.get(user=request.user)
    except APIKey.DoesNotExist:
        messages.error(request, 'You need to set up your API key first.')
        return redirect('api_key')
    
    # Create a new result
    result = ScrapingResult.objects.create(
        project=project,
        status='running',
        log_output='Initializing script generation...\n'
    )
    
    # Start the script generation and containerization in a separate thread
    thread = threading.Thread(
        target=process_script_generation,
        args=(result, project, api_key.key)
    )
    thread.daemon = True
    thread.start()
    
    return redirect('execution_status', result_id=result.id)

@login_required
def execution_status(request, result_id):
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    return render(request, 'scraper/execution_status.html', {'result': result})

@login_required
def results_screen(request, result_id):
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    
    # Parse result data based on output format
    if result.project.output_format == 'json':
        try:
            parsed_data = json.loads(result.result_data)
            result_data = json.dumps(parsed_data, indent=2)
        except json.JSONDecodeError:
            result_data = result.result_data
    else:
        result_data = result.result_data
    
    return render(request, 'scraper/results_screen.html', {
        'result': result,
        'result_data': result_data
    })

@login_required
def get_logs(request, result_id):
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    return JsonResponse({'log': result.log_output, 'status': result.status})

@login_required
def download_container(request, result_id):
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    
    # Check if we have a containerized script
    if not result.status == 'completed':
        messages.error(request, 'Container is not ready for download yet.')
        return redirect('execution_status', result_id=result.id)
    
    # In a real implementation, we would create a downloadable Docker image
    # For now, we'll just return the script as a downloadable file
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="scraper_{result.project.id}.py"'
    response.write(result.result_data)
    
    return response

def update_log(result_id, message):
    """Update the log output for a result"""
    try:
        result = ScrapingResult.objects.get(pk=result_id)
        result.log_output += message
        result.save()
    except Exception as e:
        print(f"Error updating log: {e}")

def containerize_script(script_path, output_dir=None, image_name=None):
    """Wrapper for the Containerizer class"""
    try:
        # Dynamically load the Containerizer class
        Containerizer = load_containerizer()
        containerizer = Containerizer(script_path, output_dir, image_name)
        success = containerizer.containerize()
        
        if success:
            return {
                'success': True,
                'image_name': containerizer.image_name,
                'output_dir': str(containerizer.output_dir)
            }
        else:
            return {
                'success': False,
                'error': 'Containerization failed'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def process_script_generation(result, project, api_key):
    """Process script generation and containerization in a background thread"""
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, f'scraper_{project.id}.py')
    
    try:
        # Prepare project data for script generation
        project_data = {
            'name': project.name,
            'website': project.website,
            'llm_input': project.llm_input,
            'respect_robots': project.respect_robots,
            'pagination': project.pagination,
            'delay': project.delay,
            'max_pages': project.max_pages,
            'timeout': project.timeout,
            'user_agent': project.user_agent,
            'verbose_logging': project.verbose_logging,
            'download_html': project.download_html,
            'screenshot': project.screenshot,
            'output_format': project.output_format,
            'field_specifications': []
        }
        
        # Add field specifications
        for field in project.field_specifications.all():
            project_data['field_specifications'].append({
                'field_name': field.field_name,
                'field_type': field.field_type,
                'description': field.description
            })
        
        # Define log callback function to update logs in real-time
        def log_callback(message):
            update_log(result.id, message)
        
        # Generate script using LLM
        try:
            script_content = generate_script_with_llm(project_data, api_key, log_callback)
            
            # Write script to file
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            update_log(result.id, "Script generated successfully.\nStarting containerization process...\n")
            
            # Containerize the script
            containerization_result = containerize_script(script_path)
            
            if containerization_result.get('success', False):
                update_log(result.id, f"Containerization successful. Container image: {containerization_result.get('image_name')}\n")
                result.result_data = script_content
                result.status = 'completed'
            else:
                error_message = containerization_result.get('error', 'Unknown error during containerization')
                update_log(result.id, f"Containerization failed: {error_message}\n")
                result.status = 'failed'
            
        except Exception as e:
            update_log(result.id, f"Error during script generation: {str(e)}\n")
            result.status = 'failed'
            
        result.save()
        
    except Exception as e:
        update_log(result.id, f"Unexpected error: {str(e)}\n")
        result.status = 'failed'
        result.save()