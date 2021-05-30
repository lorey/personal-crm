import django.conf
from allauth.account.forms import AddEmailForm
from allauth.account.models import EmailAddress


class AddEmailFormRespectingVerification(AddEmailForm):
    """
    This is the default AddEmailForm with the only difference
    being that it sends no verification email if ACCOUNT_EMAIL_VERIFICATION is 'none'.
    see: https://github.com/pennersr/django-allauth/issues/2876
    """

    def save(self, request):
        confirm = django.conf.settings.ACCOUNT_EMAIL_VERIFICATION != "none"
        return EmailAddress.objects.add_email(
            request, self.user, self.cleaned_data["email"], confirm=confirm
        )
