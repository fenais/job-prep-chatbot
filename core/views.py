from django.shortcuts import render
from .rag import get_rag_response

def home(request):
    return render(request, "home.html")

def chat(request):
    chat_history = request.session.get("chat_history", [])

    if request.method == "POST":
        if "clear_chat" in request.POST:
            request.session["chat_history"] = []
            return render(request, "chat.html", {"chat_history": []})

        user_message = request.POST.get("message", "").strip()

        if user_message:
            rag_data = get_rag_response(user_message)

            chat_history.append({
                "user": user_message,
                "bot": rag_data["answer"],
                "sources": rag_data["sources"] 
            })

            request.session["chat_history"] = chat_history

    return render(request, "chat.html", {
        "chat_history": chat_history
    })

def developer(request):
    return render(request, "developer.html")

def admin_dashboard(request):
    return render(request, "admin_dashboard.html")