from django.db import migrations

from core.starter_content import seed_starter_content as seed_starter_content_helper


def seed_starter_content(apps, schema_editor):
    KnowledgeDocument = apps.get_model("core", "KnowledgeDocument")
    AccuracyTestCase = apps.get_model("core", "AccuracyTestCase")
    seed_starter_content_helper(KnowledgeDocument, AccuracyTestCase)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_accuracytesting"),
    ]

    operations = [
        migrations.RunPython(seed_starter_content, migrations.RunPython.noop),
    ]
