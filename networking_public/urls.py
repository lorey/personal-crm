from django.urls import path

from . import views

app_name = "networking_public"

urlpatterns = [path("", views.index, name="index")]
