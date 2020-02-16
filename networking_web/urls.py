from django.urls import path

from . import views

app_name = "networking_web"

urlpatterns = [
    path("", views.index, name="index"),
    path("settings", views.settings, name="settings"),
    path("contacts/<int:contact_id>/add-touchpoint", views.add_touchpoint, name="add-touchpoint"),
    path(
        "contacts/<int:contact_id>/change-frequency/<str:method>",
        views.change_frequency,
        name="change-frequency",
    ),
    path("import/csv", views.import_csv_start, name="import-csv"),
]
