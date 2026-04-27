from django.core.management.base import BaseCommand

from core.models import AccuracyTestCase, KnowledgeDocument
from core.starter_content import seed_starter_content


class Command(BaseCommand):
    help = "Restore starter knowledge documents and starter accuracy test cases."

    def handle(self, *args, **options):
        results = seed_starter_content(KnowledgeDocument, AccuracyTestCase)
        self.stdout.write(
            self.style.SUCCESS(
                "Starter content synced: "
                f"{results['created_documents']} document(s) created, "
                f"{results['created_test_cases']} test case(s) created."
            )
        )
