from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import AccuracyTestCase, AccuracyTestResult, AccuracyTestRun, KnowledgeDocument
from .views import answer_matches_expected, source_matches_expected
from .rag import (
    EVALUATION_MAX_TOKENS,
    get_quick_response,
    get_rag_response,
    prepare_rag_response,
)


class AccuracyTestingFlowTests(TestCase):
    def setUp(self):
        AccuracyTestCase.objects.update(is_active=False)

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
        test_name = "Custom Cover Letter Tone"
        response = self.client.post(
            reverse("developer"),
            {
                "action": "save_test_case",
                "test_name": test_name,
                "test_question": "What tone should a cover letter use?",
                "expected_answer": "professional",
                "expected_source": "cover_letter_guide",
                "test_notes": "Checks for a grounded style answer.",
                "test_is_active": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        saved_case = AccuracyTestCase.objects.get(name=test_name)
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

    def test_answer_match_accepts_or_alternatives_with_pipe(self):
        self.assertTrue(
            answer_matches_expected(
                "skills, experience|projects|internships, role|targeting",
                "A good summary highlights technical skills, relevant projects, and the role you're targeting.",
            )
        )

    def test_answer_match_fails_when_any_required_keyword_is_missing(self):
        self.assertFalse(
            answer_matches_expected(
                "situation, task, action, result",
                "The method includes Situation, Task, and Action.",
            )
        )

    def test_source_match_accepts_multiple_expected_variants(self):
        self.assertTrue(
            source_matches_expected(
                "star_interview_guide | interview_handbook_star_method",
                ["interview_handbook_star_method", "behavioral_interview_questions_answers_examples"],
            )
        )


class QuickResponseTests(TestCase):
    def test_quick_response_handles_plain_gratitude(self):
        self.assertEqual(
            get_quick_response("thank you"),
            {"answer": "You're welcome! I'm happy to help.", "sources": []},
        )

    def test_quick_response_does_not_hijack_thank_you_note_questions(self):
        self.assertIsNone(
            get_quick_response("When should I send a thank-you note after an interview?")
        )


class RagEvaluationSpeedTests(TestCase):
    @patch("core.rag.get_collection")
    @patch("core.rag.collection_count")
    def test_prepare_rag_response_uses_single_result_in_evaluation_mode(self, mock_count, mock_get_collection):
        mock_collection = mock_get_collection.return_value
        mock_count.return_value = 5
        mock_collection.query.return_value = {
            "documents": [["Use the STAR method to structure your answer."]],
            "metadatas": [[{"source": "star_interview_guide", "topic": "Interviews"}]],
        }

        prepared = prepare_rag_response(
            "What does STAR stand for?",
            evaluation_mode=True,
        )

        self.assertEqual(prepared["kind"], "llm")
        mock_collection.query.assert_called_once_with(
            query_texts=["what does star stand for?"],
            n_results=1,
        )

    @patch("core.rag.get_anthropic_client")
    @patch("core.rag.prepare_rag_response")
    def test_get_rag_response_uses_smaller_token_budget_for_evaluation(self, mock_prepare, mock_client_factory):
        mock_prepare.return_value = {
            "kind": "llm",
            "sources": ["star_interview_guide"],
            "system_prompt": "system",
            "user_prompt": "user",
            "evaluation_mode": True,
        }

        mock_client = mock_client_factory.return_value
        mock_client.messages.create.return_value.content = [type("Block", (), {"text": "STAR means Situation, Task, Action, Result."})()]

        response = get_rag_response("What does STAR stand for?", evaluation_mode=True)

        self.assertEqual(response["sources"], ["star_interview_guide"])
        mock_client.messages.create.assert_called_once()
        self.assertEqual(
            mock_client.messages.create.call_args.kwargs["max_tokens"],
            EVALUATION_MAX_TOKENS,
        )


class StarterContentTests(TestCase):
    def test_seeded_knowledge_documents_exist(self):
        expected_sources = {
            "ats_resume_guide",
            "resume_strategy",
            "star_interview_guide",
            "technical_interview_guide",
            "cover_letter_guide",
            "internship_search_guide",
            "job_search_strategy",
            "linkedin_profile_guide",
            "networking_follow_up",
            "portfolio_github_guide",
            "recruiter_outreach_guide",
            "salary_negotiation",
        }

        existing_sources = set(
            KnowledgeDocument.objects.filter(source_label__in=expected_sources).values_list("source_label", flat=True)
        )

        self.assertSetEqual(existing_sources, expected_sources)
        self.assertTrue(
            KnowledgeDocument.objects.filter(source_label="resume_strategy", is_active=True).exists()
        )

    def test_seeded_accuracy_test_cases_exist(self):
        expected_names = {
            "ATS Resume Basics",
            "Resume Summary Essentials",
            "STAR Method Definition",
            "Technical Interview Structure",
            "Cover Letter Tone",
            "Interview Follow-Up Timing",
            "Internship Search Basics",
            "Negotiation Preparation",
            "Recruiter Outreach Tone",
        }

        existing_names = set(
            AccuracyTestCase.objects.filter(name__in=expected_names).values_list("name", flat=True)
        )

        self.assertSetEqual(existing_names, expected_names)
        self.assertTrue(
            AccuracyTestCase.objects.filter(name="STAR Method Definition", is_active=True).exists()
        )

    def test_seed_starter_content_command_restores_deleted_records(self):
        KnowledgeDocument.objects.filter(source_label="resume_strategy").delete()
        AccuracyTestCase.objects.filter(name="STAR Method Definition").delete()

        call_command("seed_starter_content")

        self.assertTrue(
            KnowledgeDocument.objects.filter(source_label="resume_strategy").exists()
        )
        self.assertTrue(
            AccuracyTestCase.objects.filter(name="STAR Method Definition").exists()
        )

    def test_seed_starter_content_command_does_not_duplicate_existing_records(self):
        initial_document_count = KnowledgeDocument.objects.count()
        initial_test_case_count = AccuracyTestCase.objects.count()

        call_command("seed_starter_content")

        self.assertEqual(KnowledgeDocument.objects.count(), initial_document_count)
        self.assertEqual(AccuracyTestCase.objects.count(), initial_test_case_count)
