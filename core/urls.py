from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/", views.chat, name="chat"),
    path("developer/", views.developer, name="developer"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
]