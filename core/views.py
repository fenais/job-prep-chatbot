from django.shortcuts import render
import re

def get_bot_response(user_message):
    message = user_message.lower().strip()
    words = re.findall(r"\b[\w']+\b", message)

    # Greetings
    if "hello" in words or "hi" in words or "hey" in words:
        return "Hey! I can help with resumes, cover letters, interviews, internships, and general job prep."

    if "how are you" in message:
        return "I am doing well, thank you. I am ready to help with your job preparation questions."

    if "bye" in words or "goodbye" in words:
        return "Goodbye! Come back anytime if you want help with job prep."

    if "thanks" in words or "thank" in words:
        return "You're welcome! I'm happy to help."

    # General help
    if "what can you do" in message or "how can you help" in message:
        return "I can answer questions about resumes, cover letters, interviews, internships, and general job preparation."

    if "help" in words and len(words) <= 3:
        return "I can help with resumes, cover letters, interviews, internships, and general job preparation."

    # Cover letter
    if ("cover" in words and "letter" in words) or "coverletter" in words:
        if "start" in words or "begin" in words:
            return "A strong cover letter usually starts by stating the role you are applying for, why you are interested in it, and why you are a good fit."
        if "write" in words or "make" in words:
            return "A strong cover letter should explain why you are interested in the role, how your skills fit the position, and why you would be a strong candidate."
        return "A cover letter should connect your experience to the role and show why you are genuinely interested."

    # Resume
    if "resume" in words or "resumes" in words:
        if "bullet" in words or "bullets" in words:
            return "Strong resume bullets should start with action verbs, describe what you did clearly, and include results or impact when possible."
        if "skills" in words:
            return "Your resume skills section should include relevant technical and professional skills that match the role you are applying for."
        if "project" in words or "projects" in words:
            return "When listing projects on a resume, describe what you built, what tools you used, and what impact or result the project had."
        return "A strong resume should be clear, concise, and focused on your skills, projects, and achievements."

    # Interview
    if "interview" in words or "interviews" in words:
        if "behavioral" in words:
            return "For behavioral interviews, use clear examples from your experience. A common method is STAR: Situation, Task, Action, Result."
        if "technical" in words:
            return "For technical interviews, practice solving problems step by step, explain your thinking clearly, and talk through your solution."
        if "prepare" in words or "advice" in words or "practice" in words:
            return "For interviews, it helps to practice common questions, speak clearly, and use examples from your experience."
        return "Interview preparation usually includes practicing common questions, reviewing your experience, and preparing clear examples."

    # Internship / jobs
    if "internship" in words or "internships" in words:
        if "get" in words or "find" in words:
            return "To get an internship, build a strong resume, apply consistently, prepare for interviews, and network with recruiters and professionals."
        return "Internship preparation usually includes improving your resume, applying early, and practicing interview questions."

    if "job" in words or "jobs" in words:
        if "search" in words or "find" in words or "finding" in words:
            return "A good job search strategy includes tailoring your resume, applying consistently, networking, and following up when appropriate."
        return "When applying for jobs, make sure to tailor your resume, prepare for interviews, and keep track of your applications."

    if "apply" in words or "application" in words or "applications" in words:
        return "When applying, make sure your resume matches the role, follow the instructions carefully, and keep track of deadlines and submissions."

    # Networking
    if "network" in words or "networking" in words or "linkedin" in words:
        return "Networking works best when you introduce yourself clearly, ask thoughtful questions, and follow up politely."

    if "recruiter" in words or "recruiters" in words:
        return "When speaking to a recruiter, introduce yourself clearly, mention your interests, and ask specific questions about the role or team."

    # Career / job prep
    if "career" in words:
        return "Career preparation often includes building experience, improving your application materials, networking, and practicing communication skills."

    return "I am not sure how to answer that yet, but I can help with resumes, cover letters, and job interviews."


def home(request):
    return render(request, "home.html")


def chat(request):
    chat_history = request.session.get("chat_history", [])

    if request.method == "POST":
        if "clear_chat" in request.POST:
            request.session["chat_history"] = []
            return render(request, "chat.html", {
                "chat_history": []
            })

        user_message = request.POST.get("message", "").strip()

        if user_message:
            response = get_bot_response(user_message)

            chat_history.append({
                "user": user_message,
                "bot": response
            })

            request.session["chat_history"] = chat_history

    return render(request, "chat.html", {
        "chat_history": chat_history
    })

def developer(request):
    return render(request, "developer.html")


def admin_dashboard(request):
    return render(request, "admin_dashboard.html")