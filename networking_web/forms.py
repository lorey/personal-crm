from django import forms

from networking_base.models import Contact


class CreateContactForm(forms.ModelForm):
    class Meta:
        model = Contact
