STARTER_KNOWLEDGE_DOCUMENTS = [
    {
        "title": "Resume Strategy Playbook",
        "source_label": "resume_strategy",
        "topic": "Resume",
        "is_active": True,
        "content": (
            "A strong resume should be tailored to the target role instead of reused unchanged. "
            "Lead with a short professional summary that names the target role, years of relevant experience, "
            "strongest skills, and one or two measurable results. Keep the summary focused on evidence, not vague claims. "
            "Each experience bullet should start with a strong action verb, describe a specific task, and end with a measurable outcome such as revenue, time saved, quality improvement, user growth, or performance gains. "
            "Use keywords from the job description in natural language so the resume stays readable while still performing well in applicant tracking systems. "
            "Place the most relevant projects, tools, and technical skills where a recruiter can scan them quickly. "
            "For students and early-career candidates, projects can be as important as internships when they demonstrate ownership, collaboration, and impact. "
            "Avoid paragraphs, generic objective statements, and long lists of soft skills without proof."
        ),
    },
    {
        "title": "Behavioral Interview STAR Guide",
        "source_label": "star_interview_guide",
        "topic": "Interviews",
        "is_active": True,
        "content": (
            "The STAR method is a reliable framework for answering behavioral interview questions. "
            "STAR stands for Situation, Task, Action, and Result. "
            "Situation explains the context, Task explains your responsibility, Action explains the steps you personally took, and Result explains the measurable outcome or lesson learned. "
            "Good STAR answers are specific, chronological, and concise. "
            "Use one main example per answer, quantify the outcome when possible, and spend the most time on the Action because that shows how you think and work. "
            "Prepare stories about teamwork, conflict, leadership, failure, prioritization, and learning something quickly."
        ),
    },
    {
        "title": "Technical Interview Preparation Guide",
        "source_label": "technical_interview_guide",
        "topic": "Interviews",
        "is_active": True,
        "content": (
            "In a technical interview, start by clarifying the problem, inputs, outputs, and constraints before jumping into code. "
            "A strong structure is: restate the problem, ask clarifying questions, describe a brute-force approach, explain the optimized solution, and test the final answer with examples or edge cases. "
            "Interviewers care about communication as much as correctness, so narrate tradeoffs and assumptions out loud. "
            "When discussing complexity, mention both time and space complexity. "
            "If you get stuck, say what you know, propose a smaller step, and keep moving instead of going silent."
        ),
    },
    {
        "title": "Cover Letter Writing Guide",
        "source_label": "cover_letter_guide",
        "topic": "Cover Letters",
        "is_active": True,
        "content": (
            "A cover letter should sound specific, concise, and professional rather than generic. "
            "Open by naming the role and why the company or mission matters to you. "
            "In the body, connect two or three experiences directly to the job requirements using outcomes and examples instead of repeating the resume line by line. "
            "Show knowledge of the company, team, product, or problem space. "
            "Close with a confident but respectful call to continue the conversation. "
            "One page is enough for most applications."
        ),
    },
    {
        "title": "Networking and Interview Follow-Up",
        "source_label": "networking_follow_up",
        "topic": "Networking",
        "is_active": True,
        "content": (
            "After an interview, send a thank-you note within 24 to 48 hours. "
            "Mention one or two specific discussion points so the message feels personal instead of templated. "
            "A networking message should be short, polite, and easy to answer. "
            "Ask for insight or advice before asking for referrals, and make it clear why you chose that person. "
            "Following up once is appropriate; repeated messages without new context can hurt your impression."
        ),
    },
    {
        "title": "Salary Negotiation Basics",
        "source_label": "salary_negotiation",
        "topic": "Offers",
        "is_active": True,
        "content": (
            "Salary negotiation should be collaborative, informed, and grounded in market data. "
            "Before negotiating, research the market range for the role, level, and location. "
            "When responding to an offer, express enthusiasm first, then discuss compensation using evidence such as scope, skills, competing data, or interview performance. "
            "Consider total compensation, including base salary, bonus, equity, benefits, and signing bonus. "
            "Avoid ultimatums unless you are fully prepared to walk away."
        ),
    },
]


STARTER_ACCURACY_TESTS = [
    {
        "name": "Resume Summary Essentials",
        "question": "What should a resume summary include for a software engineering candidate?",
        "expected_answer": "skills, experience|projects|internships, role|targeting",
        "expected_source": "resume_summary_guide | resume_strategy | career_center_resume_guide",
        "notes": "Checks that the answer highlights the core parts of the starter resume guide.",
        "is_active": True,
    },
    {
        "name": "STAR Method Definition",
        "question": "What does STAR stand for in a behavioral interview answer?",
        "expected_answer": "situation, task, action, result",
        "expected_source": "star_interview_guide",
        "notes": "Validates the behavioral interview framework explanation.",
        "is_active": True,
    },
    {
        "name": "STAR Method Source Check",
        "question": "How should I use the STAR method in a behavioral interview answer?",
        "expected_answer": "situation, task, action, result",
        "expected_source": "star_interview_guide | interview_handbook_star_method | star_method_guide",
        "notes": "Accepts any of the STAR-focused guides as a valid cited source.",
        "is_active": True,
    },
    {
        "name": "Technical Interview Structure",
        "question": "How should I structure my answer in a coding interview?",
        "expected_answer": "clarifying questions, brute force, optimized solution, test",
        "expected_source": "technical_interview_guide",
        "notes": "Verifies the chatbot returns the expected technical interview sequence.",
        "is_active": True,
    },
    {
        "name": "Cover Letter Tone",
        "question": "What tone should a cover letter use?",
        "expected_answer": "specific, concise, professional",
        "expected_source": "cover_letter_guide",
        "notes": "Confirms grounded advice on cover letter tone.",
        "is_active": True,
    },
    {
        "name": "Interview Follow-Up Timing",
        "question": "When should I send a thank-you note after an interview?",
        "expected_answer": "24, 48",
        "expected_source": "networking_follow_up",
        "notes": "Makes sure follow-up timing is retrieved correctly.",
        "is_active": True,
    },
    {
        "name": "Negotiation Preparation",
        "question": "What should I prepare before negotiating a job offer?",
        "expected_answer": "market range, evidence, compensation",
        "expected_source": "salary_negotiation",
        "notes": "Checks that negotiation advice is informed and practical.",
        "is_active": True,
    },
]


def seed_starter_content(KnowledgeDocument, AccuracyTestCase):
    created_documents = 0
    created_test_cases = 0

    for document in STARTER_KNOWLEDGE_DOCUMENTS:
        _, created = KnowledgeDocument.objects.get_or_create(
            source_label=document["source_label"],
            defaults=document,
        )
        if created:
            created_documents += 1

    for test_case in STARTER_ACCURACY_TESTS:
        _, created = AccuracyTestCase.objects.get_or_create(
            name=test_case["name"],
            defaults=test_case,
        )
        if created:
            created_test_cases += 1

    return {
        "created_documents": created_documents,
        "created_test_cases": created_test_cases,
        "total_documents": len(STARTER_KNOWLEDGE_DOCUMENTS),
        "total_test_cases": len(STARTER_ACCURACY_TESTS),
    }
