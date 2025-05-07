# Automatic Web Scraper Generator

**A tool for journalists and non-technical users to generate Python scraping scripts from URL.**

## Overview
This tool simplifies web scraping by allowing users to provide a prompt, URL, and desired of a website and automatically generating a **Python script** to extract the desired data. It combines **LLM (Large Language Model) analysis**, **containerized execution**, and **user-friendly input** to make scraping accessible without requiring coding expertise.

### Key Features
✅ **No-Code Scraping** – Generate scraping scripts just by providing a URL and prompt.  
✅ **LLM-Powered Parsing** – Uses AI to intelligently identify and extract structured data.  
✅ **Dockerized Environment** – Ensures consistent execution across different systems.  
✅ **Customizable Output** – Supports CSV, JSON, or direct database storage.  
✅ **User-Friendly CLI** – Simple commands to run and configure scrapers.  

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Docker (for containerized execution)
- OpenAI API key (for LLM processing)

### 1. Clone the Repository
```bash
git clone https://github.com/cros-nash/ds490.git
```

### 2. Create and activate a virtual environment + Install Dependencies
```bash
python -m venv mvenv
source myenv/bin/activate
cd ds490
pip install -e .
playwright install
```
### 3. Configure Environment Variables
Create a `.env` file and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

### 4. Create database:
```
   python frontend/manage.py makemigrations
   python frontend/manage.py migrate
```

### 5. Create a superuser (admin account):
   ```
   python frontend/manage.py createsuperuser
   ```
   Follow the prompts to set username, email, and password.

## Accessing Web App:
1. Run the development server:
   ```
   python frontend/manage.py runserver
   ```

2. To access application, enter in browser: http://127.0.0.1:8000/

3. Login with superuser credentials

4. Set API key

5. Create project

### Working Example:
* name of project: test 3
* website url: https://crawlee.dev/python/docs/examples
* prompt="Please give me the name, description, and URL for examples of crawlee applications that involve pagination"
* fields:
    * name: str = Name of the example
    * description: str = One sentence description of the example
    * url: str = description="URL of the example

## Technical Stack
### Core Language: Python 3.10+
#### Web Scraping Libraries: BeautifulSoup4, Scrapy, Playwright
#### AI Integration: OpenAI GPT models
#### Containerization: Docker
#### Data Formats: CSV, JSON, SQLite

## Roadmap
#### Add GUI interface
#### Support for PDF inputs
#### Multi-language output support
#### Cloud deployment options

## MIT License

Copyright (c) [2025] [Crosby Nash, Inhye Kang, Claire Law, Andrew Botolino, Langdon White]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
See full license text at: https://opensource.org/licenses/MIT

## Creative Commons Attribution-NonCommercial 4.0

You are free to:
- Share — copy and redistribute the material
- Adapt — remix, transform, and build upon the material

Under these terms:
- Attribution — You must give credit
- NonCommercial — You may not use for commercial purposes

See full license at: https://creativecommons.org/licenses/by-nc/4.0/
