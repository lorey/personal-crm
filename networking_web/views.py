from collections import defaultdict
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from pytz import UTC

from networking_base.models import Contact, ContactStatus, Interaction

CONTACT_FIELDS_DEFAULT = [
    "name",
    "frequency_in_days",
    "description",
    "linkedin_url",
    "twitter_url",
    "phone_number",
]


class ContactListView(ListView):
    model = Contact
    template_name = "web/_atomic/pages/contacts-overview.html"
    ordering = "name"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        contacts = context["contact_list"]
        contacts_by_status = defaultdict(list)
        for contact in contacts:
            contacts_by_status[contact.get_status()].append(contact)

        # add counts
        contact_counts = {
            "all": len(contacts),
            "out_of_touch": len(contacts_by_status.get(ContactStatus.OUT_OF_TOUCH, [])),
            "in_touch": len(contacts_by_status.get(ContactStatus.IN_TOUCH, [])),
            "hidden": len(contacts_by_status.get(ContactStatus.HIDDEN, [])),
        }
        context.update({k + "_count": v for k, v in contact_counts.items()})

        # filter status
        status = None
        status_raw = self.request.GET.get("status", None)
        if status_raw:
            # get status enum
            status = ContactStatus(int(self.request.GET.get("status")))

            # re-filter contacts
            context["contact_list"] = list(
                filter(lambda c: c.get_status() == status, contacts)
            )

        return context


class ContactDetailView(DetailView):
    model = Contact
    template_name = "web/_atomic/pages/contacts-detail.html"


class ContactUpdateView(UpdateView):
    model = Contact
    fields = CONTACT_FIELDS_DEFAULT
    template_name = "web/_atomic/pages/contacts_form.html"

    def get_success_url(self):
        return reverse("networking_web:contact-view", kwargs={"pk": self.object.id})


class ContactCreateView(CreateView):
    model = Contact
    fields = CONTACT_FIELDS_DEFAULT
    template_name = "web/_atomic/pages/contacts_form.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user_id = self.request.user.id
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("networking_web:contact-view", kwargs={"pk": self.object.id})


class ContactDeleteView(DeleteView):
    model = Contact
    template_name = "web/_atomic/pages/contacts_confirm_delete.html"

    def get_success_url(self):
        success_url = reverse("networking_web:index")
        return success_url


class InteractionListView(ListView):
    model = Interaction
    template_name = "web/_atomic/pages/interactions-overview.html"
    ordering = "-was_at"


@login_required
def index(request):
    contacts = (
        Contact.objects.filter(user=request.user)
        .order_by("name")
        .prefetch_related("interactions")
        .all()
    )

    contacts = sorted(contacts, key=lambda c: c.get_urgency(), reverse=True)
    return render(
        request,
        "web/_atomic/pages/dashboard.html",
        {"contacts": list(contacts)},
    )


@login_required
def add_touchpoint(request, contact_id):
    contact = Contact.objects.get(pk=contact_id)
    assert contact.user == request.user
    Interaction.objects.create(
        was_at=datetime.now(tz=UTC),
        contact=contact,
        title="Interaction",
        description="...",
    )
    return redirect_back(request)


def redirect_back(request):
    referer = request.META.get("HTTP_REFERER")
    return HttpResponseRedirect(referer)
