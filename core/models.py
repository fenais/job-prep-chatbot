from django.db import models


class KnowledgeDocument(models.Model):
    title = models.CharField(max_length=200)
    source_label = models.CharField(max_length=255)
    topic = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "-updated_at"]

    def __str__(self):
        return self.title
    
from django.db import models

class PerformanceLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    question = models.TextField(blank=True)
    latency_ms = models.FloatField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    source_count = models.IntegerField(default=0)

    def __str__(self):
        status = "Success" if self.success else "Failure"
        return f"{self.timestamp} - {status} - {self.latency_ms:.2f} ms"
