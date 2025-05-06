""" defining models - each has a database table with the listed fields.
models need to be listed in frontend/settings.py"""

from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    website = models.URLField()
    llm_input = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # optional settings - main interface
    respect_robots = models.BooleanField(default=True)
    pagination = models.BooleanField(default=False)
    delay = models.IntegerField(default=1)  # Seconds between requests
    max_pages = models.IntegerField(default=10)
    timeout = models.IntegerField(default=30)  # Seconds
    user_agent = models.CharField(max_length=255, blank=True)
    verbose_logging = models.BooleanField(default=False)
    download_html = models.BooleanField(default=False)
    screenshot = models.BooleanField(default=False)
    output_format = models.CharField(max_length=10, choices=[('csv', 'CSV'), ('json', 'JSON')], default='json')
    
    def __str__(self):
        return self.name

class FieldSpecification(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='field_specifications')
    field_name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=[
        ('str', 'String'), 
        ('int', 'Integer'), 
        ('float', 'Float'),
        ('bool', 'Boolean'),
        ('date', 'Date'),
        ('list', 'List'),
        ('dict', 'Dictionary')
    ], default='str')
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)  # To maintain field order
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.field_name} ({self.field_type})"
    
class APIKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    provider = models.CharField(max_length=50, default='openai')
    
    def __str__(self):
        return f"{self.user.username}'s {self.provider} API Key"

class ScrapingResult(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='results')
    created_at = models.DateTimeField(auto_now_add=True)
    result_data = models.TextField()  # Stores JSON or CSV as text
    status = models.CharField(max_length=20, 
                             choices=[('running', 'Running'), 
                                     ('completed', 'Completed'),
                                     ('failed', 'Failed')],
                             default='running')
    log_output = models.TextField(blank=True)
    
    def __str__(self):
        return f"Result for {self.project.name} - {self.created_at}"