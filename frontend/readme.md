### Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/web-scraping-tool.git
   cd web-scraping-tool
   ```

2. Create and activate a virtual environment + install dependencies:
   ```
   python -m venv mvenv
   source myenv/bin/activate
   pip install django requests django-widget-tweaks
   ```

3. Create database:
    ```
   python manage.py makemigrations
   python manage.py migrate
   ```

4. Create a superuser (admin account):
   ```
   python manage.py createsuperuser
   ```
   Follow the prompts to set username, email, and password.

## Accessing Web App:
1. Run the development server:
   ```
   python manage.py runserver
   ```

2. To access application, enter in browser: http://127.0.0.1:8000/
