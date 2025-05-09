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
import zipfile

from django.conf import settings
import io, contextlib
from pydantic import create_model
from typing import List
from scripts.container import Containerizer


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
@login_required
def get_logs(request, result_id):
    """Return the current log and status, plus the generated script if available."""
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    data = {
        'log': result.log_output,
        'status': result.status,
        'script': result.result_data or ''
    }
    return JsonResponse(data)

@login_required
def download_container(request, result_id):
    result = get_object_or_404(ScrapingResult, pk=result_id, project__user=request.user)
    # Check if we have a containerized script
    if not result.status == 'completed':
        messages.error(request, 'Container is not ready for download yet.')
        return redirect('execution_status', result_id=result.id)
    
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, f'scraper_{result.project.id}.py')

    with open(script_path, 'w') as f:
        f.write(result.result_data)
    
    zip_path = os.path.join(temp_dir, 'container_package.zip')
    try:
        # Containerize the script (if not already containerized)
        container_result = containerize_script(script_path, temp_dir)
        if not container_result.get('success', False):
            messages.error(request, 'Failed to package container files.')
            return redirect('project_detail', pk=result.project.id)
        # create zip file with all the container files
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(script_path, os.path.basename(script_path)) # add generated script
            containerfile_path = os.path.join(temp_dir, 'Containerfile') 
            if os.path.exists(containerfile_path):
                zipf.write(containerfile_path, 'Containerfile') # Add the Containerfile
            req_path = os.path.join(temp_dir, 'requirements.txt')
            if os.path.exists(req_path):
                zipf.write(req_path, 'requirements.txt') # Add the requirements.txt
        with open(zip_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{result.project.name}_container.zip"'
            return response
    except Exception as e:
        messages.error(request, f'Error packaging container: {str(e)}')
        return redirect('project_detail', pk=result.project.id)
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


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
    full_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../../{script_path}'))
    try:
        containerizer = Containerizer(full_script_path, output_dir, image_name)
        if containerizer.containerize():
            print(f"\nContainerization complete. \nRun your container using:")
            print(f"docker run {containerizer.image_name}")
            return {
                'success': True,
                'image_name': containerizer.image_name,
                'output_dir': str(containerizer.output_dir)
            }
        else:
            print("\nContainerization failed. Please check the errors above.")
            return {
                'success': False,
                'error': 'Containerization failed'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def generate_python_script_template(project):
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
        INDENT = " " * 4
        clean_name = fs.field_name.strip()
        clean_desc = fs.description.replace("'", "\\'").replace("\n", " ").replace("\r", "").strip()
        record_fields.append(f"{INDENT}{clean_name}: {pytype} = Field(..., description='{clean_desc}')")

    if not record_fields:
        record_fields = ["    pass"]

    # Template for the script
    template = f'''\
import os
os.environ["OPENAI_API_KEY"] = "{api_key}"
from pydantic import BaseModel, Field
from typing import List{", Any" if needs_any else ""}
{"import datetime" if needs_datetime else ""}
from graphs.code_generator_graph import CodeGeneratorGraph

graph_config = {{
"llm": {{
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": "openai/gpt-4o-mini"
}},
"verbose": {bool(project.verbose_logging)},
"headless": False,
"output_file_name": "extracted_data.py",
"force": {True},
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
print("Code generated successfully")
'''
    return template

def process_script_generation(result, project, api_key):
    """
    Generate a Python scraping script for the project, store it in the result,
    and update the log and status.
    """
    # Ensure fresh database connection for this background thread
    try:
        from django.db import close_old_connections
        close_old_connections()
    except Exception:
        # Could not reset DB connections; continue anyway
        pass
    update_log(result.id, "Generating Python script based on project specifications...\n")

    try:
        script_content = generate_python_script_template(project)
        update_log(result.id, "Script generated successfully.\n")
    except Exception as e:
        update_log(result.id, f"Error generating script: {e}\n")
        result.status = 'failed'
        result.save()
        return
    
    update_log(result.id, "Writing script to temporary file and executing...\n")
    # Determine the repository root (parent of BASE_DIR)
    from pathlib import Path
    project_root = Path(settings.BASE_DIR).parent
    
    # Write script to a temporary file and execute it unbuffered
    tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    try:
        tmp_file.write(script_content)
        tmp_file.flush()
        tmp_file.close()
        # Run the script with unbuffered output
        cmd = [sys.executable, '-u', tmp_file.name]
        update_log(result.id, f"Executing command: {' '.join(cmd)}\n")
        update_log(result.id, f"Working dir: {project_root}\n")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            update_log(result.id, f"Subprocess started with PID {proc.pid}\n")
            try:
                for line in proc.stdout:
                    line = proc.stdout.readline()
                    update_log(result.id, line)
                exit_code = proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                proc.kill()
                update_log(result.id, f"Subprocess exited \n")
        except Exception as e:
            update_log(result.id, f"Subprocess error: {e}\n")
            exit_code = -1
    finally:
        # Clean up the temporary script file
        try:
            os.remove(tmp_file.name)
        except OSError:
            pass
         
    update_log(result.id, f"Script execution completed with exit code {exit_code}.\n")
    if exit_code == 0:
        output_file = os.path.join(project_root, "extracted_data.py")
        try:
            with open(output_file, 'r') as f:
                generated_data = f.read()
            update_log(result.id, "Generated data file read successfully.\n")
            result.result_data = generated_data
            result.status = 'completed'
        except Exception as e:
            update_log(result.id, f"Error reading generated file: {e}\n")
            result.result_data = ''
            result.status = 'failed'
    else:
        result.result_data = ''
        result.status = 'failed'
    result.save()