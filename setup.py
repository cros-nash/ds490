from setuptools import setup, find_packages

setup(
    name="ds490",  # this is the package name
    version="0.1.0",
    packages=find_packages(exclude=["tests", "frontend", "databases", "storage", "__pycache__"]),
    install_requires=[
        # List your project's runtime dependencies here, for example:
        "pydantic>=1.10.0",
        "langchain>=0.0.1",
        "scrapegraphai>=0.1.0",
        # Add others from requirements.txt or your own needs
    ],
    author="Your Name",
    author_email="you@example.com",
    description="DS490 smart scraper pipeline",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ds490",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)