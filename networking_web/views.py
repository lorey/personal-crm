import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from pytz import UTC

from networking_base.models import Contact, Touchpoint
from networking_base.views import (
    create_contacts_from_file_handle,
    create_contacts_from_trello,
)

CONTACT_FIELDS_DEFAULT = [
    "name",
    "frequency_in_days",
    "description",
    "email",
    "linkedin_url",
    "twitter_username",
    "phone_number",
]


class ContactListView(ListView):
    model = Contact
    template_name = "web/contact_overview.html"
    ordering = "name"


class ContactDetailView(DetailView):
    model = Contact
    template_name = "web/contact_detail.html"


class ContactUpdateView(UpdateView):
    model = Contact
    fields = CONTACT_FIELDS_DEFAULT
    template_name = "web/contact_form.html"

    def get_success_url(self):
        return reverse("networking_web:contact-view", kwargs={"pk": self.object.id})


class ContactCreateView(CreateView):
    model = Contact
    fields = CONTACT_FIELDS_DEFAULT
    template_name = "web/contact_form.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user_id = self.request.user.id
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("networking_web:contact-view", kwargs={"pk": self.object.id})


class ContactDeleteView(DeleteView):
    model = Contact
    template_name = "web/contact_confirm_delete.html"

    def get_success_url(self):
        success_url = reverse("networking_web:index")
        return success_url


@login_required
def index(request):
    contacts = (
        Contact.objects.filter(user=request.user)
        .order_by("name")
        .prefetch_related("touchpoint_set")
        .all()
    )

    query = request.GET.get("search")
    if query:
        contacts = filter(lambda c: query.lower() in c.name.lower(), contacts)

    is_show_all = request.GET.get("all") == "true"
    if not is_show_all:
        contacts_urgent = (c for c in contacts if c.get_urgency() > 0)
        contacts = sorted(contacts_urgent, key=lambda c: c.get_urgency(), reverse=True)
    return render(
        request,
        "web/index.html",
        {"contacts": list(contacts), "is_show_all": is_show_all, "query": query},
    )


@login_required
def settings(request):
    return render(request, "web/settings.html")


@login_required
def add_touchpoint(request, contact_id):
    contact = Contact.objects.get(pk=contact_id)
    assert contact.user == request.user
    Touchpoint.objects.create(when=datetime.now(tz=UTC), contact=contact)
    return redirect_back(request)


@login_required
def change_frequency(request, contact_id, method):
    contact = Contact.objects.get(pk=contact_id)
    assert contact.user == request.user
    methods = {"increase": 2, "decrease": 0.5}
    # make sure frequency stays positive
    contact.frequency_in_days = max(contact.frequency_in_days * methods[method], 1)
    contact.save()
    return redirect_back(request)


@login_required
def import_csv_start(request):
    if request.method == "POST":
        content = request.FILES["csv"]
        owner = request.user
        col_name = "Name"
        col_email = "E-mail 1 - Value"
        contacts = create_contacts_from_file_handle(content, owner, col_email, col_name)
        for c in contacts:
            defaults = {k: getattr(c, k) for k in ["frequency_in_days"]}
            o_new, was_created = Contact.objects.get_or_create(
                name=c.name, email=c.email, user=request.user, defaults=defaults
            )

        return redirect("networking_web:index")
    return render(request, "web/import-csv.html")


@login_required
def import_trello_start(request):
    if request.method == "POST":
        json_data = json.load(request.FILES["json"].open())
        create_contacts_from_trello(json_data, request.user)
        return redirect("networking_web:index")
    return render(request, "web/import-trello.html")


def redirect_back(request):
    referer = request.META.get("HTTP_REFERER")
    return HttpResponseRedirect(referer)
