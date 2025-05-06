import os
from setuptools import setup, find_packages

setup(
    name="ds490",  # this is the package name
    version="0.1.0",
    packages=find_packages(exclude=["tests", "frontend", "databases", "storage", "__pycache__"]),
    # Automatically load install requirements from requirements.txt
    install_requires=[
        line for line in (
            req.strip() for req in open(
                os.path.join(os.path.dirname(__file__), 'requirements.txt'),
                encoding='utf-8'
            ).read().splitlines()
        )
        # skip empty lines, comments, and editable/VCS entries
        if line
           and not line.startswith('#')
           and not line.startswith('-')
           and 'git+' not in line
    ],
    author="Your Name",
    author_email="you@example.com",
    description="DS490 smart scraper pipeline",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cros-nash/ds490",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)