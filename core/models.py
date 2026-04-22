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


class AccuracyTestCase(models.Model):
    name = models.CharField(max_length=120)
    question = models.TextField()
    expected_answer = models.TextField(
        blank=True,
        help_text="Optional phrase or keyword expected to appear in the chatbot answer.",
    )
    expected_source = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional source label expected to be cited by the chatbot.",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "-updated_at"]

    def __str__(self):
        return self.name


class AccuracyTestRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_cases = models.IntegerField(default=0)
    passed_cases = models.IntegerField(default=0)
    failed_cases = models.IntegerField(default=0)
    average_latency_ms = models.FloatField(default=0)
    status = models.CharField(max_length=20, default="completed")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Accuracy run {self.id} at {self.started_at:%Y-%m-%d %H:%M:%S}"


class AccuracyTestResult(models.Model):
    run = models.ForeignKey(AccuracyTestRun, on_delete=models.CASCADE, related_name="results")
    test_case = models.ForeignKey(AccuracyTestCase, on_delete=models.CASCADE, related_name="results")
    chatbot_answer = models.TextField(blank=True)
    returned_sources = models.TextField(blank=True)
    answer_match = models.BooleanField(default=False)
    source_match = models.BooleanField(default=False)
    passed = models.BooleanField(default=False)
    latency_ms = models.FloatField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["test_case__name", "-created_at"]

    def __str__(self):
        return f"{self.test_case.name} - {'PASS' if self.passed else 'FAIL'}"

    @property
    def returned_sources_list(self):
        if not self.returned_sources:
            return []
        return [source.strip() for source in self.returned_sources.split(",") if source.strip()]


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
