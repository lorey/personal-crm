from django.urls import path

from . import views

app_name = "networking_web"

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "contacts/<int:contact_id>/add-touchpoint", views.add_touchpoint, name="add-touchpoint"
    ),
]
