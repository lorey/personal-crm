from datetime import datetime

from django import forms

from networking_base.models import Contact, Interaction


class CreateContactForm(forms.ModelForm):
    class Meta:
        exclude = []
        model = Contact


class InteractionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(InteractionForm, self).__init__(*args, **kwargs)
        self.fields["contacts"].queryset = Contact.objects.order_by("name")
        self.fields["was_at"].initial = datetime.now().astimezone()

    class Meta:
        fields = ["title", "description", "was_at", "contacts"]
        model = Interaction
