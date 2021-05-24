from datetime import datetime, timedelta
from enum import Enum

from django.contrib.auth.models import User
from django.db import models

LAST_INTERACTION_DEFAULT = datetime.now().astimezone() - timedelta(days=365)


class ContactStatus(Enum):
    HIDDEN = -1
    IN_TOUCH = 1
    OUT_OF_TOUCH = 2


class Contact(models.Model):
    name = models.CharField(max_length=50)
    frequency_in_days = models.IntegerField()
    user = models.ForeignKey(User, models.CASCADE)

    # contact details
    description = models.TextField(null=True, blank=True)
    linkedin_url = models.URLField(max_length=100, null=True, blank=True)
    twitter_url = models.URLField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)

    def get_last_interaction(self):
        return self.interactions.order_by("-was_at").first()

    def get_last_interaction_date_or_default(self):
        li = self.get_last_interaction()
        lid = LAST_INTERACTION_DEFAULT
        if li:
            lid = li.was_at
        return lid

    def get_urgency(self):
        last_interaction_date = self.get_last_interaction_date_or_default()
        time_since_interaction = datetime.now().astimezone() - last_interaction_date
        return time_since_interaction.days - self.frequency_in_days

    def get_due_date(self):
        last_interaction_date = self.get_last_interaction_date_or_default()
        return last_interaction_date + timedelta(days=self.frequency_in_days)

    def get_status(self):
        if self.get_urgency() > 0:
            return ContactStatus.OUT_OF_TOUCH
        return ContactStatus.IN_TOUCH

    def __str__(self):
        return self.name


class EmailAddress(models.Model):
    contact = models.ForeignKey(Contact, models.CASCADE, related_name="emails")
    email = models.EmailField(max_length=100)

    class Meta:
        unique_together = ("contact", "email")


class InteractionType(models.Model):
    """
    The type of interaction
    """

    slug = models.SlugField()
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=250)


class Interaction(models.Model):
    """
    An interaction with a specific contact.
    """

    contact = models.ForeignKey(Contact, models.CASCADE, related_name="interactions")
    type = models.ForeignKey(InteractionType, models.SET_NULL, blank=True, null=True)

    title = models.CharField(max_length=100)
    description = models.TextField()
    was_at = models.DateTimeField()

    def __str__(self):
        return f"{self.contact.user}: {self.contact} at {self.was_at}"


class EmailInteraction(Interaction):
    gmail_message_id = models.CharField(max_length=100)


class CalendarInteraction(Interaction):
    google_calendar_id = models.CharField(max_length=100)
    url = models.URLField()


class Reminder(models.Model):
    """Reminder to get in touch when a contact is due."""

    due_on = models.DateField()
    skipped_at = models.DateTimeField()
