""" 
views = functions that process http requests and return responses
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .models import Project, ScrapingResult, APIKey
from .forms import ProjectForm, APIKeyForm, CustomUserCreationForm
import json
import os
import tempfile
import subprocess
import threading
import time

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

@login_required         # restricts acesss to logged-in users only
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
            messages.success(request, f'Project "{project.name}" created successfully.')
            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm()
        
    return render(request, 'scraper/create_project.html', {'form': form})

@login_required
def edit_project(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project "{project.name}" updated successfully.')
            return redirect('project_detail', pk=project.id)
    else:
        form = ProjectForm(instance=project)
        
    return render(request, 'scraper/edit_project.html', {'form': form, 'project': project})

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
    
    return render(request, 'scraper/project_detail.html', {
        'project': project,
        'results': results
    })

@login_required
def generate_script(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    
    # Create script template based on project settings
    script_content = generate_python_script(project)
    
    # Create a new result
    result = ScrapingResult.objects.create(
        project=project,
        status='running',
        log_output='Initializing...\n'
    )
    
    # Start the script generation and containerization in a separate thread
    thread = threading.Thread(
        target=process_script_generation,
        args=(result, script_content, project)
    )
    thread.start()
    
    return redirect('execution_status', result_id=result.id)

@login_required
def execution_status(request, result_id):
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    
    return render(request, 'scraper/execution_status.html', {'result': result})

@login_required
def result_detail(request, result_id):
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
    
    return render(request, 'scraper/result_detail.html', {
        'result': result,
        'result_data': result_data
    })

@login_required
def get_logs(request, result_id):
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    return JsonResponse({'log': result.log_output, 'status': result.status})

@login_required
def download_container(request, result_id):
    # Logic to create a downloadable container file
    # This would typically create a tarball of the Docker image
    # For simplicity, we're just returning a text file
    response = HttpResponse(content_type='application/text')
    response['Content-Disposition'] = f'attachment; filename="docker_commands.txt"'
    
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    project = result.project
    
    response.write(f"# Docker commands to run your scraper\n\n")
    response.write(f"# Pull the image\ndocker pull scraper-{project.id}\n\n")
    response.write(f"# Run the container\ndocker run scraper-{project.id}\n")
    
    return response

# helper functions
def generate_python_script(project):
    # TODO: return scrapegraph script
    return NotImplemented

def process_script_generation(result, script_content, project):
    """Process script generation and containerization in a background thread"""
    # Create a temporary file for the script
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, f'scraper_{project.id}.py')
    
    try:
        # Update log
        result.log_output += "Creating script file...\n"
        result.save()
        
        # Write script to file
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Update log
        result.log_output += "Script file created successfully.\n"
        result.log_output += "Analyzing dependencies...\n"
        result.save()
        
        # Simulate containerization process
        time.sleep(2)
        
        # Update log
        result.log_output += "Dependencies identified: requests, beautifulsoup4, pandas\n"
        result.log_output += "Creating Containerfile...\n"
        result.save()
        
        # Simulate more processing
        time.sleep(2)
        
        # Update log with container file content
        container_file = f"""FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scraper_{project.id}.py .
CMD ["python", "scraper_{project.id}.py"]"""
        
        result.log_output += "Containerfile created:\n"
        result.log_output += container_file + "\n\n"
        result.log_output += "Building container image...\n"
        result.save()
        
        # Simulate building container
        time.sleep(3)
        
        # Update log
        result.log_output += "Container built successfully.\n"
        result.log_output += "Container image tag: scraper-" + str(project.id) + "\n"
        result.log_output += "Ready for download or execution.\n"
        
        # Set example result data
        sample_data = [
            {"text": "Home", "url": "/"},
            {"text": "About", "url": "/about"},
            {"text": "Contact", "url": "/contact"}
        ]
        
        if project.output_format == 'json':
            result.result_data = json.dumps(sample_data, indent=2)
        else:
            # Convert to CSV format as a string
            csv_data = "text,url\n"
            for item in sample_data:
                csv_data += f"{item['text']},{item['url']}\n"
            result.result_data = csv_data
        
        result.status = 'completed'
        result.save()
        
    except Exception as e:
        # Handle errors
        result.log_output += f"Error: {str(e)}\n"
        result.status = 'failed'
        result.save()