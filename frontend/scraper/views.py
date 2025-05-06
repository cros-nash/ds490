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
    """AJAX endpoint to add a new field specification row"""
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
    """
    Generate a Python script that uses CodeGeneratorGraph to produce
    scraping code based on project settings and field specifications.
    """
    from .models import APIKey
    import json

    # Retrieve API key
    try:
        api_key = APIKey.objects.get(user=project.user).key
    except APIKey.DoesNotExist:
        raise ValueError("API key not found for user")

    # Prepare field specs
    specs = list(project.field_specifications.all())
    # Decide extra imports
    needs_datetime = any(fs.field_type == "date" for fs in specs)
    needs_any = any(fs.field_type == "list" for fs in specs)

    # Build the Record class fields
    type_map = {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "date": "datetime.date",
        "list": "List[Any]",
        "dict": "dict",
    }
    record_fields = []
    for fs in specs:
        pytype = type_map.get(fs.field_type, "str")
        desc = fs.description.replace("'", "\\'")
        record_fields.append(f"    {fs.field_name}: {pytype} = Field(..., description='{desc}')")
    if not record_fields:
        record_fields = ["    pass"]

    # Template for the script
    template = f'''\
import os
os.environ["OPENAI_API_KEY"] = "{api_key}"
from pydantic import BaseModel, Field
from typing import List{", Any" if needs_any else ""}
{"import datetime" if needs_datetime else ""}
from code_generator_graph import CodeGeneratorGraph

graph_config = {{
"llm": {{
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": "openai/gpt-4o-mini"
}},
"verbose": {project.verbose_logging},
"headless": False
}}  

class Record(BaseModel):
    {chr(10).join(record_fields)}

class RecordList(BaseModel):
    records: List[Record]

if __name__ == "__main__":
    graph = CodeGeneratorGraph(
        prompt={json.dumps(project.llm_input)},
        source={json.dumps(project.website)},
        config=graph_config,
        schema=RecordList
    )
result = graph.run()
print(result)
'''
    return template

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
        
        # Run the generated script to produce code
        result.log_output += "Running code generator script...\n"
        result.save()
        # Execute the script and capture output
        proc = subprocess.run(
            ["python", script_path],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        # Log stdout and stderr
        result.log_output += proc.stdout or ''
        if proc.stderr:
            result.log_output += "Errors during generation:\n" + proc.stderr + "\n"
        # Save generated code as result data and mark completion
        result.result_data = proc.stdout or ''
        result.status = 'completed'
        result.save()
        
    except Exception as e:
        # Handle errors
        result.log_output += f"Error: {str(e)}\n"
        result.status = 'failed'
        result.save()