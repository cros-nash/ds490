import os
import tempfile
import subprocess
import importlib.util
import sys
from pathlib import Path

def load_containerizer():
    """Load the Containerizer class from the containerizer.py file."""
    # Assuming containerizer.py is in the same directory as this file
    module_path = os.path.join(os.path.dirname(__file__), 'containerizer.py')
    
    spec = importlib.util.spec_from_file_location("containerizer", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module.Containerizer

def containerize_script(script_path, output_dir=None, image_name=None):
    """Containerize a Python script using the Containerizer class."""
    try:
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