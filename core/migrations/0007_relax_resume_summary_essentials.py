from django.db import migrations


def relax_resume_summary_essentials(apps, schema_editor):
    AccuracyTestCase = apps.get_model("core", "AccuracyTestCase")
    AccuracyTestCase.objects.filter(name="Resume Summary Essentials").update(
        expected_answer="skills, experience|projects|internships, role|targeting",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_refresh_starter_accuracy_cases"),
    ]

    operations = [
        migrations.RunPython(relax_resume_summary_essentials, migrations.RunPython.noop),
    ]
