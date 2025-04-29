import argparse
import sys
import os
import ast
import subprocess # for running shell commands
from pathlib import Path
from importlib.metadata import distributions
import pkg_resources


class Containerizer:
    IMPORT_TO_PACKAGE_MAP = {
        'bs4': 'beautifulsoup4',
        'PIL': 'pillow',
        'sklearn': 'scikit-learn',
        'cv2': 'opencv-python',
        'yaml': 'pyyaml',
        'wx': 'wxpython',
        'psycopg2': 'psycopg2-binary',
        'dateutil': 'python-dateutil',
        'skimage': 'scikit-image',
        'dotenv': 'python-dotenv',
        'sqlalchemy': 'SQLAlchemy',
    }

    def __init__(self, 
                 script_path,       # Path to generated Python script
                 output_dir=None,   # Directory to store generated files (default: same directory as script)
                 image_name=None):  # Name for the Container image (default: script name in lowercase)
        self.script_path: str = Path(script_path)
        if not self.script_path.exists():
            raise FileNotFoundError(f'{script_path} not found.')
        self.output_dir: str = Path(output_dir) if output_dir else self.script_path.parent
        self.output_dir.mkdir(exist_ok=True)         # Output will be in same directory as the given script if not otherwise specified
        self.image_name: str = image_name or self.script_path.stem         # image name is same as given script's name if not specified
        self.imports = set()
        self.requirements = set()        
        self.stdlib_modules = self._get_stdlib_modules()
        # dictionary entries are package:version 
        self.installed_packages = {dist.metadata['Name'].lower(): dist.version for dist in distributions()}
        self._build_distribution_map = self._build_distribution_map()

    def _build_distribution_map(self):
        """Build a mapping from top-level modules to their distribution packages."""
        dist_map = {}
        
        for dist in pkg_resources.working_set:
            try:                # Get metadata and top-level modules
                if dist.has_metadata('top_level.txt'):
                    for module in dist.get_metadata('top_level.txt').splitlines():
                        if module:  # Skip empty lines
                            dist_map[module] = dist.project_name
            except Exception:
                continue       # Skip if we can't get metadata
        for import_name, package_name in self.IMPORT_TO_PACKAGE_MAP.items():
            dist_map[import_name] = package_name         # Add our manual mappings
        return dist_map
    
    def get_package_for_import(self, import_name):
        """Get the package name for a given import name."""
        if import_name in self.distribution_map:
            return self.distribution_map[import_name]
        if import_name in self.IMPORT_TO_PACKAGE_MAP:
            return self.IMPORT_TO_PACKAGE_MAP[import_name]
        return import_name #default to import name itself
    
    def _get_stdlib_modules(self):
        """Get standard library modules."""
        stdlib = set(sys.builtin_module_names) # add builtin modules
        stdlib_dir = Path(os.__file__).parent
        for path in stdlib_dir.glob('*.py'):
            stdlib.add(path.stem)              # add modules in standard library directory
        stdlib.update({'json', 'datetime', 'logging', 'collections',  # added some manually because they keep getting missed -- might be more.
                       'functools', 'itertools', 'unittest', 'argparse'})                    
        return stdlib
    
    def parse_imports(self
                      ) -> bool:  # returns True if successful, False otherwise
        """Parse the script and get import statements."""
        with open(self.script_path, 'r') as file:
            try:
                tree = ast.parse(file.read())
            except SyntaxError as e:
                print(f"Error parsing {self.script_path}: {e}")
                return False
        for node in ast.walk(tree):
            # Handle 'import module' statements
            if isinstance(node, ast.Import):
                for name in node.names:
                    self.imports.add(name.name.split('.')[0])  # Get the top-level module
            # Handle 'from module import submodule' statements
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.imports.add(node.module.split('.')[0])  # Get the top-level module
        return True


    def identify_requirements(self
                              ) -> bool: #  returns True if successful, False otherwise
        """Parse the script to extract imports and identify required packages."""
        if not self.parse_imports():
            return False
        
        for module_name in self.imports:
            if module_name in self.stdlib_modules:
                continue # skip standard library modules
            if module_name.lower() in self.installed_packages:
                self.requirements.add(f"{module_name}=={self.installed_packages[module_name.lower()]}")
            else:
                self.requirements.add(module_name)
    
        print(f"Added {len(self.requirements)} external dependencies to requirements.txt:")
        for req in self.requirements:
            print(f'* {req}')

        return True
    
    def generate_requirements_file(self
                                   ) -> str:    # path to requirements.txt 
        requirements_path = self.output_dir / "requirements.txt"
        with open(requirements_path, 'w') as file:
            for req in sorted(self.requirements):
                file.write(f"{req}\n")
        return requirements_path
    

    def create_containerfile(self
                             ) -> str:          # path to Containerfile
            containerfile_path = self.output_dir / "Containerfile"
            script_name = self.script_path.name
            with open(containerfile_path, 'w') as file:
                file.write(f"FROM python:{sys.version_info.major}.{sys.version_info.minor}\n\n")
                file.write("WORKDIR /app\n\n")
                file.write("COPY requirements.txt .\n")
                file.write("RUN pip install --no-cache-dir -r requirements.txt\n\n")
                file.write(f"COPY {script_name} .\n\n")
                file.write(f'CMD ["python", "{script_name}"]\n')
            return containerfile_path
    

    def build_docker_image(self
                           ) -> bool:  #  returns True if successful, False otherwise
            containerfile_path = self.create_containerfile()
            script_name = self.script_path.name
            # Copy the script to the output directory if it's not already there
            if self.script_path.parent != self.output_dir:
                target_script = self.output_dir / script_name
                with open(self.script_path, 'rb') as src, open(target_script, 'wb') as dst:
                    dst.write(src.read())
            try:
                subprocess.run(
                    ["docker", "build", "-f", "Containerfile", "-t", self.image_name, str(self.output_dir)],
                    check=True
                )
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error building Container image: {e}")
                return False
            except FileNotFoundError:
                print("Docker command not found. Is Docker installed and available in PATH?")
                return False
    

    def containerize(self) -> bool:
        """execute full containerization pipeline"""
        if not self.identify_requirements():
            return False
        self.generate_requirements_file()
        if not self.build_docker_image():
            return False
        return True



def main():
    parser = argparse.ArgumentParser(description="Analyze a Python script, install its dependencies, \
                                     and create a container.")
    
    # parse command line arguments
    parser.add_argument("script", 
                        help="Path to generated Python script")
    parser.add_argument("-o", "--output-dir",
                        help="Directory to store generated files (default: same directory as script)")
    parser.add_argument("-n", "--image-name", 
                        help="Name for the Container image (default: script name in lowercase)")
    
    args = parser.parse_args() 
    
    # create container object and execute pipeline
    containerizer = Containerizer(args.script, args.output_dir, args.image_name)
    if containerizer.containerize():
        print(f"\nContainerization complete. \nRun your container using:")
        print(f"docker run {containerizer.image_name}")
    else:
        print("\nContainerization failed. Please check the errors above.")

    # TODO: run the container
    # https://qmacro.org/blog/posts/2025/03/23/how-i-run-executables-in-containers/
    # push image to public registry/repo 
    # we can pull it from registry and run it for them 
    # or they can run it locally

    # put code in the container

    # output should be local not in container
    # go to dir where you want output to be
    # docker run -v current_dir
    
    # executable container - slightly different way to create them 
    # instead of cmd to run container, use entry point (consistently works for executable container)
    # docker run scraper. 
    # google "executable container"
    # 
    # entry point cowsay
    # docker run cowsaycontainer will show the cow.


if __name__ == '__main__':
    main()