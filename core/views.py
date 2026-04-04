from django.shortcuts import render

def home(request):
    return render(request, "home.html")

def chat(request):
    response = ""
    user_message = ""

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()
        if user_message:
            response = "This is a placeholder chatbot response."

    return render(request, "chat.html", {
        "response": response,
        "user_message": user_message
    })

def developer(request):
    return render(request, "developer.html")

def admin_dashboard(request):
    return render(request, "admin_dashboard.html")