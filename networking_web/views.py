from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from pytz import UTC

from networking_base.models import Contact, Touchpoint


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
        contacts = sorted(contacts_urgent, key=lambda c: c.get_urgency())
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
    methods = {"increase": 1, "decrease": -1}
    # make sure frequency stays positive
    contact.frequency_in_days = max(contact.frequency_in_days + methods[method], 1)
    contact.save()
    return redirect_back(request)


def redirect_back(request):
    referer = request.META.get("HTTP_REFERER")
    return HttpResponseRedirect(referer)
