from django.contrib import admin
from .models import AccuracyTestCase, AccuracyTestResult, AccuracyTestRun, PerformanceLog

admin.site.register(PerformanceLog)
admin.site.register(AccuracyTestCase)
admin.site.register(AccuracyTestRun)
admin.site.register(AccuracyTestResult)
