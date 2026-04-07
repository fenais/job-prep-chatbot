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
