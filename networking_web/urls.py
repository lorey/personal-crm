from django.urls import path

from . import views

app_name = "networking_web"

urlpatterns = [
    path("", views.index, name="index"),
    # interactions
    path(
        "interactions",
        views.InteractionListView.as_view(),
        name="interactions-overview",
    ),
    path(
        "interactions/create",
        views.InteractionCreateView.as_view(),
        name="interaction-create",
    ),
    # contacts
    path("contacts", views.ContactListView.as_view(), name="contact-overview"),
    path("contacts/create", views.ContactCreateView.as_view(), name="contact-create"),
    path("contacts/<int:pk>", views.ContactDetailView.as_view(), name="contact-view"),
    path(
        "contacts/<int:pk>/edit",
        views.ContactUpdateView.as_view(),
        name="contact-update",
    ),
    path(
        "contacts/<int:pk>/delete",
        views.ContactDeleteView.as_view(),
        name="contact-delete",
    ),
    path(
        "contacts/<int:contact_id>/add-touchpoint",
        views.add_touchpoint,
        name="add-touchpoint",
    ),
]
