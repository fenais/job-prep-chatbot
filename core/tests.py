from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import AccuracyTestCase, AccuracyTestResult, AccuracyTestRun
from .views import answer_matches_expected


class AccuracyTestingFlowTests(TestCase):
    def test_run_accuracy_tests_saves_run_and_result(self):
        test_case = AccuracyTestCase.objects.create(
            name="Resume Basics",
            question="What should a resume summary include?",
            expected_answer="skills and experience",
            expected_source="resume_guide",
            is_active=True,
        )

        with patch(
            "core.views.get_rag_response",
            return_value={
                "answer": "A strong summary highlights your skills and experience.",
                "sources": ["resume_guide"],
            },
        ) as mocked_rag:
            response = self.client.post(
                reverse("developer"),
                {"action": "run_accuracy_tests"},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccuracyTestRun.objects.count(), 1)

        test_run = AccuracyTestRun.objects.get()
        result = AccuracyTestResult.objects.get(run=test_run, test_case=test_case)

        self.assertEqual(test_run.total_cases, 1)
        self.assertEqual(test_run.passed_cases, 1)
        self.assertEqual(test_run.failed_cases, 0)
        self.assertTrue(result.passed)
        self.assertTrue(result.answer_match)
        self.assertTrue(result.source_match)
        mocked_rag.assert_called_once_with(test_case.question, evaluation_mode=True)

    def test_run_accuracy_tests_marks_failures_when_expectations_do_not_match(self):
        AccuracyTestCase.objects.create(
            name="Interview Prep",
            question="How should I answer behavioral questions?",
            expected_answer="STAR method",
            expected_source="behavioral_interviews",
            is_active=True,
        )

        with patch(
            "core.views.get_rag_response",
            return_value={
                "answer": "Practice concise examples and stay calm.",
                "sources": ["general_tips"],
            },
        ):
            self.client.post(reverse("developer"), {"action": "run_accuracy_tests"})

        test_run = AccuracyTestRun.objects.get()
        result = AccuracyTestResult.objects.get(run=test_run)

        self.assertEqual(test_run.passed_cases, 0)
        self.assertEqual(test_run.failed_cases, 1)
        self.assertFalse(result.passed)
        self.assertFalse(result.answer_match)
        self.assertFalse(result.source_match)

    def test_save_test_case_creates_case(self):
        response = self.client.post(
            reverse("developer"),
            {
                "action": "save_test_case",
                "test_name": "Cover Letter Tone",
                "test_question": "What tone should a cover letter use?",
                "expected_answer": "professional",
                "expected_source": "cover_letter_guide",
                "test_notes": "Checks for a grounded style answer.",
                "test_is_active": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        saved_case = AccuracyTestCase.objects.get(name="Cover Letter Tone")
        self.assertEqual(saved_case.expected_source, "cover_letter_guide")
        self.assertTrue(saved_case.is_active)


class AccuracyMatcherTests(TestCase):
    def test_answer_match_accepts_keyword_lists(self):
        self.assertTrue(
            answer_matches_expected(
                "situation, task, action, result",
                "The STAR method includes Situation, Task, Action, and Result.",
            )
        )

    def test_answer_match_accepts_multiple_line_checks(self):
        self.assertTrue(
            answer_matches_expected(
                "situation, task, action, result\nstructured framework",
                "The STAR method is a structured framework with Situation, Task, Action, and Result.",
            )
        )

    def test_answer_match_fails_when_any_required_keyword_is_missing(self):
        self.assertFalse(
            answer_matches_expected(
                "situation, task, action, result",
                "The method includes Situation, Task, and Action.",
            )
        )
