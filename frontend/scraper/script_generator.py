import os
import json
import tempfile
import sys
import importlib.util
from typing import Dict, Any, List, Callable
from pydantic import BaseModel, Field, create_model

def load_code_generator_graph():
    """Dynamically load CodeGeneratorGraph from repository root"""
    # Determine repository root (three levels up from this file: scraper -> frontend -> repo)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    module_path = os.path.join(project_root, 'code_generator_graph.py')
    
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Could not find code_generator_graph.py at {module_path}")
    
    # Ensure repository root is on sys.path so that code_generator_graph imports its local modules
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    spec = importlib.util.spec_from_file_location("code_generator_graph", module_path)
    module = importlib.util.module_from_spec(spec)
    # Execute module to load CodeGeneratorGraph and its dependencies
    spec.loader.exec_module(module)
    
    return module.CodeGeneratorGraph

def dynamic_model_from_fields(fields_data: List[Dict[str, str]]) -> BaseModel:
    """Create a Pydantic model dynamically from field specifications."""
    field_definitions = {}
    
    for field in fields_data:
        field_name = field['field_name']
        field_type = field['field_type']
        field_desc = field['description']
        
        # Map string type names to actual Python types
        type_mapping = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'date': str,  # Use str for dates initially
            'list': list,
            'dict': dict
        }
        
        python_type = type_mapping.get(field_type, str)
        field_definitions[field_name] = (python_type, Field(description=field_desc))
    
    # Create the dynamic model
    DynamicModel = create_model('DynamicModel', **field_definitions)
    return DynamicModel

def generate_script(project_data: Dict[str, Any], api_key: str, log_callback: Callable[[str], None] = None) -> str:
    """
    Generate a scraping script using CodeGeneratorGraph.
    
    Args:
        project_data: Project configuration
        api_key: API key for LLM
        log_callback: Function to call with log updates
    
    Returns:
        str: Generated Python script
    """
    if log_callback:
        log_callback("Initializing script generation...\n")
    
    # Extract field specifications for schema creation
    field_specs = project_data.get('field_specifications', [])
    
    # Create a dynamic Pydantic model based on field specifications
    DynamicModel = dynamic_model_from_fields(field_specs)
    
    # Prepare config for CodeGeneratorGraph
    graph_config = {
        "llm": {
            "api_key": api_key,
            "model": "claude-3-haiku-20240307",  # or configure based on provider
        },
        "verbose": True,
        "headless": False,
        "reduction": 2,
        "max_iterations": {
            "overall": 3,
            "syntax": 3,
            "execution": 3,
            "validation": 3,
            "semantic": 3,
        },
        "filename": "extracted_data.py",
    }
    
    # Create a temporary directory for script generation
    temp_dir = tempfile.mkdtemp()
    graph_config["output_dir"] = temp_dir
    
    if log_callback:
        log_callback("Preparing LLM prompt...\n")
    
    # Create user prompt from project data
    prompt = f"Scrape data from {project_data['website']}. {project_data['llm_input']}"
    
    # Add advanced settings to prompt if needed
    if project_data.get('respect_robots', True):
        prompt += " Respect robots.txt rules."
    
    if project_data.get('pagination', False):
        prompt += f" Handle pagination with max pages set to {project_data.get('max_pages', 10)}."
    
    if project_data.get('delay', 1) > 0:
        prompt += f" Use a delay of {project_data.get('delay', 1)} seconds between requests."
    
    if log_callback:
        log_callback(f"Using prompt: {prompt}\n")
        log_callback("Loading code generator graph module...\n")
    
    # Dynamically load CodeGeneratorGraph
    try:
        CodeGeneratorGraph = load_code_generator_graph()
        
        if log_callback:
            log_callback("Creating code generator instance...\n")
        
        # Create and run the code generator
        try:
            code_generator = CodeGeneratorGraph(
                prompt=prompt,
                source=project_data['website'],
                schema=DynamicModel,
                config=graph_config
            )
            
            if log_callback:
                log_callback("Generating script with LLM...\n")
            
            generated_code = code_generator.run()
            
            if log_callback:
                log_callback("Script generation successful!\n")
                log_callback(f"```python\n{generated_code[:1000]}...\n```\n")
            
            return generated_code
        except Exception as e:
            error_msg = f"Error during script generation: {str(e)}"
            if log_callback:
                log_callback(f"{error_msg}\n")
            raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Failed to load CodeGeneratorGraph module: {str(e)}"
        if log_callback:
            log_callback(f"{error_msg}\n")
        raise ImportError(error_msg)