from django.db import migrations

from core.starter_content import seed_starter_content


def add_more_starter_topics(apps, schema_editor):
    KnowledgeDocument = apps.get_model("core", "KnowledgeDocument")
    AccuracyTestCase = apps.get_model("core", "AccuracyTestCase")
    seed_starter_content(KnowledgeDocument, AccuracyTestCase)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_relax_resume_summary_essentials"),
    ]

    operations = [
        migrations.RunPython(add_more_starter_topics, migrations.RunPython.noop),
    ]
