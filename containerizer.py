import argparse
import sys
import os
import ast
import subprocess # for running shell commands
from pathlib import Path
from importlib.metadata import distributions

class Containerizer:
    def __init__(self, script_path, output_dir=None, image_name=None):
        self.script_path: str = Path(script_path)
        if not self.script_path.exists():
            raise FileNotFoundError(f'{script_path} not found.')

        # Output will be in same directory as the given script if not otherwise specified
        self.output_dir: str = Path(output_dir) if output_dir else self.script_path.parent
        self.output_dir.mkdir(exist_ok=True)

        # image name is same as given script's name if not specified
        self.image_name: str = image_name or self.script_path.stem

        # set of standard library modules
        self.stdlib_modules = set(sys.builtin_module_names) | {
            path.stem for path in Path(os.__file__).parent.glob('*.py')
        }
        # dictionary entries are package:version 
        self.installed_packages = {dist.metadata['Name'].lower(): dist.version for dist in distributions()}
        
        self.imports = set()
        self.requirements = set()

    def parse_imports(self):
        """Parse the script and extract all import statements."""
        with open(self.script_path, 'r') as file:
            try:
                tree = ast.parse(file.read())
            except SyntaxError as e:
                print(f"Error parsing {self.script_path}: {e}")
                return False
        
        # Look for import statements
        for node in ast.walk(tree):
            # Handle 'import module' statements
            if isinstance(node, ast.Import):
                for name in node.names:
                    self.imports.add(name.name.split('.')[0])  # Get the top-level module
            
            # Handle 'from module import submodule' statements
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.imports.add(node.module.split('.')[0])  # Get the top-level module
        
        return True

    def identify_requirements(self):
        """
        Parse the script to extract imports and identify required packages.
        Returns True if successful, False otherwise.
        """
        # Read and parse the script
        try:
            with open(self.script_path, 'r') as file:
                tree = ast.parse(file.read())
        except SyntaxError as e:
            print(f"Error parsing {self.script_path}: {e}")
            return False
        except Exception as e:
            print(f"Error reading {self.script_path}: {e}")
            return False
        
        # Extract import statements and process them in one pass
        imports = set()
        
        # Walk the AST to find import statements
        for node in ast.walk(tree):
            # Handle 'import module' statements
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name.split('.')[0])  # Get the top-level module
            
            # Handle 'from module import submodule' statements
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split('.')[0])  # Get the top-level module
        
        # Process the imports to identify requirements
        for module_name in imports:
            # Skip standard library modules
            if module_name in self.stdlib_modules:
                continue

            # Check if it's an installed package
            if module_name in self.installed_packages:
                self.requirements.add(f"{module_name}=={self.installed_packages[module_name]}")
            else:
                # It might be a subdirectory or a missing package
                print(f"Note: '{module_name}' not found as installed package, adding to requirements.txt.")
                self.requirements.add(module_name)
        
        print(f"Found {len(imports)} imports, identified {len(self.requirements)} external dependencies.")
        return True
    
    def generate_requirements_file(self):
        """Generate a requirements.txt file."""
        requirements_path = self.output_dir / "requirements.txt"
        with open(requirements_path, 'w') as file:
            for req in sorted(self.requirements):
                file.write(f"{req}\n")
        return requirements_path

    def create_dockerfile(self):
            containerfile_path = self.output_dir / "Containerfile"
        
            script_name = self.script_path.name
            
            with open(dockerfile_path, 'w') as file:
                file.write(f"FROM python:{sys.version_info.major}.{sys.version_info.minor}\n\n")
                file.write("WORKDIR /app\n\n")
                
                # Copy requirements first to leverage Docker cache
                file.write("COPY requirements.txt .\n")
                file.write("RUN pip install --no-cache-dir -r requirements.txt\n\n")
                
                # Copy the script
                file.write(f"COPY {script_name} .\n\n")
                
                # Set the entrypoint
                file.write(f'CMD ["python", "{script_name}"]\n')
            
            return dockerfile_path

    def build_docker_image(self):
            """Build the Docker image."""
            dockerfile_path = self.create_dockerfile()
            script_name = self.script_path.name
            
            # Copy the script to the output directory if it's not already there
            if self.script_path.parent != self.output_dir:
                target_script = self.output_dir / script_name
                with open(self.script_path, 'rb') as src, open(target_script, 'wb') as dst:
                    dst.write(src.read())
            
            try:
                print(f"Building Docker image: {self.image_name}...")
                subprocess.run(
                    ["docker", "build", "-t", self.image_name, str(self.output_dir)],
                    check=True
                )
                print(f"Docker image '{self.image_name}' built successfully.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error building Docker image: {e}")
                return False
            except FileNotFoundError:
                print("Docker command not found. Is Docker installed and available in PATH?")
                return False

    def containerize(self):
        """execute full containerization pipeline"""
        # parse import statements in given script
        self.parse_imports
        
        self.build_docker_image 

        print(f"\nContainerization complete! You can run your script using:")
        print(f"docker run {self.image_name}")

def main():
    # parse command line arguments    
    parser = argparse.ArgumentParser(
        description="Analyze a Python script, install its dependencies, and create a Docker container."
    )
    parser.add_argument("script", help="Path to the Python script to containerize")
    parser.add_argument(
        "-o", "--output-dir", 
        help="Directory to store generated files (default: same directory as script)"
    )
    parser.add_argument(
        "-n", "--image-name", 
        help="Name for the Docker image (default: script name in lowercase)"
    )
    args = parser.parse_args() 
    
    # create container object and execute pipeline
    containerizer = Containerizer(args.script, args.output_dir, args.image_name)
    containerizer.containerize()

    #TODO: run the container
    # https://qmacro.org/blog/posts/2025/03/23/how-i-run-executables-in-containers/
    # push image to public registry/repo 
    # we can pull it from registry and run it for them 
    # or they can run it locally

    # put code in the container

    # output should be local not in container
    # go to dir where you want output to be
    # docker run -v current_dir
    
    #executable container - slightly different way to create them 
    # instead of cmd to run container, use entry point (consistently works for executable container)
    # docker run scraper. 
    # google "executable container"
    # 
    # entry point cowsay
    # docker run cowsaycontainer will show the cow.


if __name__ == '__main__':
    main()