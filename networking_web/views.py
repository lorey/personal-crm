from django.shortcuts import render

from networking_base.models import Contact


def index(request):
    contacts = Contact.objects.prefetch_related("touchpoint_set").all()
    contacts_by_urgency = sorted(contacts, key=lambda c: c.get_urgency(), reverse=True)
    return render(request, "web/index.html", {"contacts": contacts_by_urgency})
