import os
import tempfile
import subprocess
import importlib.util
import sys
from pathlib import Path

def load_containerizer():
    # TODO: fix - assumes containerizer.py is in the same directory as this file but its not
    module_path = os.path.join(os.path.dirname(__file__), 'containerizer.py')
    
    spec = importlib.util.spec_from_file_location("containerizer", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module.Containerizer

def containerize_script(script_path, output_dir=None, image_name=None):
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