from django.db import migrations

from core.starter_content import STARTER_ACCURACY_TESTS


def refresh_starter_accuracy_cases(apps, schema_editor):
    AccuracyTestCase = apps.get_model("core", "AccuracyTestCase")
    starter_cases = {
        test_case["name"]: test_case for test_case in STARTER_ACCURACY_TESTS
    }

    for name, starter_case in starter_cases.items():
        AccuracyTestCase.objects.filter(name=name).update(
            question=starter_case["question"],
            expected_answer=starter_case["expected_answer"],
            expected_source=starter_case["expected_source"],
            notes=starter_case["notes"],
            is_active=starter_case["is_active"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_update_starter_accuracy_cases"),
    ]

    operations = [
        migrations.RunPython(refresh_starter_accuracy_cases, migrations.RunPython.noop),
    ]
