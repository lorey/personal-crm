import typing
from datetime import datetime, timedelta
from enum import Enum

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count
from django.urls import reverse

LAST_INTERACTION_DEFAULT = datetime.now().astimezone() - timedelta(days=365)

CONTACT_FREQUENCY_DEFAULT = None


class ContactStatus(Enum):
    HIDDEN = -1
    IN_TOUCH = 1
    OUT_OF_TOUCH = 2


class Contact(models.Model):
    """
    A user's contact.
    """

    name = models.CharField(max_length=50)
    frequency_in_days = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(User, models.CASCADE)

    # contact details
    description = models.TextField(null=True, blank=True)
    linkedin_url = models.URLField(max_length=100, null=True, blank=True)
    twitter_url = models.URLField(max_length=100, null=True, blank=True)

    def get_last_interaction(self) -> "Interaction":
        return self.interactions.order_by("-was_at").first()

    def get_last_interaction_date_or_default(self) -> datetime:
        li = self.get_last_interaction()
        lid = LAST_INTERACTION_DEFAULT
        if li:
            lid = li.was_at
        return lid

    def get_urgency(self) -> int:
        """
        Gets integer-based urgency to contact. Higher is more urgent.
        :return:
        """
        if not self.frequency_in_days:
            return 0

        last_interaction_date = self.get_last_interaction_date_or_default()
        time_since_interaction = datetime.now().astimezone() - last_interaction_date
        return time_since_interaction.days - self.frequency_in_days

    def get_due_date(self) -> typing.Optional[datetime]:
        if not self.frequency_in_days:
            return None

        last_interaction_date = self.get_last_interaction_date_or_default()
        return last_interaction_date + timedelta(days=self.frequency_in_days)

    def get_status(self):
        if not self.frequency_in_days:
            return ContactStatus.HIDDEN

        if self.get_urgency() > 0:
            return ContactStatus.OUT_OF_TOUCH
        return ContactStatus.IN_TOUCH

    def get_absolute_url(self):
        return reverse("networking_web:contact-view", kwargs={"pk": self.id})

    def __str__(self):
        return self.name


class ContactDuplicate(models.Model):
    """
    A potential duplicate.
    """

    contact = models.ForeignKey(Contact, models.CASCADE, related_name="+")
    other_contact = models.ForeignKey(Contact, models.CASCADE, related_name="+")
    similarity = models.FloatField()


class EmailAddress(models.Model):
    """
    A contact's email address.
    """

    contact = models.ForeignKey(Contact, models.CASCADE, related_name="email_addresses")
    email = models.EmailField(max_length=100)

    class Meta:
        unique_together = ("contact", "email")


class PhoneNumber(models.Model):
    """
    A contact's phone number.
    """

    contact = models.ForeignKey(Contact, models.CASCADE, related_name="phone_numbers")
    phone_number = models.CharField(max_length=50)


class InteractionType(models.Model):
    """
    The type of interaction.
    """

    slug = models.SlugField()
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=250)


class Interaction(models.Model):
    """
    An interaction with a specific contact.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="interactions"
    )
    contacts = models.ManyToManyField(Contact, related_name="interactions")
    type = models.ForeignKey(InteractionType, models.SET_NULL, blank=True, null=True)

    title = models.CharField(max_length=100)
    description = models.TextField()
    was_at = models.DateTimeField()
    # is_outgoing = models.BooleanField()

    def __str__(self):
        return f"{self.user}: {self.title} at {self.was_at}"


#
# Google
#


class GoogleEmail(models.Model):
    # link to social account and delete if social account gets deleted
    social_account = models.ForeignKey(SocialAccount, models.CASCADE)

    # link to created interaction (if any)
    interaction = models.ForeignKey(
        Interaction, models.SET_NULL, "google_emails", null=True
    )

    gmail_message_id = models.CharField(max_length=100)
    data = models.JSONField()


class GoogleCalendarEvent(models.Model):
    # link to social account and delete if social account gets deleted
    social_account = models.ForeignKey(SocialAccount, models.CASCADE)

    # link to created interaction (if any)
    interaction = models.ForeignKey(
        Interaction, models.SET_NULL, "google_calendar_events", null=True
    )

    # google id
    google_calendar_id = models.CharField(max_length=100)

    # data
    data = models.JSONField()


#
# helpers
#


def get_recent_contacts(user, limit=5, timespan_days=14) -> typing.List[Contact]:
    """
    Fetch contacts recently interacted with.
    :param user: user
    :param limit: limit
    :param timespan_days: definition of recent in days
    :return: recent contacts
    """
    timespan_recent = datetime.now().astimezone() - timedelta(days=timespan_days)
    contacts_recent = (
        Contact.objects.filter(interactions__was_at__gt=timespan_recent)
        .filter(user=user)
        .annotate(count=Count("interactions"))
        .order_by("-count")[:limit]
    )
    return list(contacts_recent)


def get_frequent_contacts(user, limit=5) -> typing.List[Contact]:
    """
    Fetch contacts with frequent interactions.
    :param user: user
    :param limit: limit
    :return: frequent contacts
    """
    contacts_frequent = (
        Contact.objects.filter(user=user)
        .annotate(count=Count("interactions"))
        .order_by("-count")[:limit]
    )
    return list(contacts_frequent)


def get_due_contacts(user) -> typing.List[Contact]:
    """
    Fetch due contacts and sort by urgency (desc).
    :param user: user
    :return: due contacts
    """
    contacts = (
        Contact.objects.filter(user=user)
        .order_by("name")
        .prefetch_related("interactions")
        .all()
    )
    contacts = filter(lambda c: c.get_urgency() > 0, contacts)
    contacts = sorted(contacts, key=lambda c: c.get_urgency(), reverse=True)
    return list(contacts)


def get_or_create_contact_email(email: str, user) -> EmailAddress:
    """
    Get or create an email address object.

    :param email: raw email
    :param user: owning user
    :return: existing or created email address
    """
    email_clean = clean_email(email)
    ea = EmailAddress.objects.filter(email=email_clean, contact__user=user).first()
    if not ea:
        # email does not exist
        # -> create contact (dummy) and email
        contact = Contact.objects.create(
            user=user, name=email, frequency_in_days=CONTACT_FREQUENCY_DEFAULT
        )
        ea = EmailAddress.objects.create(email=email_clean, contact=contact)
    return ea


def clean_email(email: str):
    """
    Clean an email address.
    :param email: input
    :return: cleaned email
    """
    return email.lower()
