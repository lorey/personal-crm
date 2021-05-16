from django.contrib.auth.models import User
from django.db import models


class Contact(models.Model):
    name = models.CharField(max_length=50)
    frequency_in_days = models.IntegerField()
    user = models.ForeignKey(User, models.CASCADE)

    # contact details
    description = models.TextField(null=True, blank=True)
    linkedin_url = models.URLField(max_length=100, null=True, blank=True)
    twitter_url = models.URLField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)

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

    contact = models.ForeignKey(Contact, models.CASCADE)
    type = models.ForeignKey(InteractionType, models.SET_NULL, blank=True, null=True)

    title = models.CharField(max_length=100)
    description = models.TextField()
    was_at = models.DateTimeField()

    def __str__(self):
        return f"{self.contact.user}: {self.contact} at {self.was_at}"


class EmailInteraction(Interaction):
    gmail_message_id = models.CharField(max_length=100)


class CalendarInteraction(Interaction):
    # todo event id or something
    pass


class Reminder(models.Model):
    """Reminder to get in touch when a contact is due."""

    due_on = models.DateField()
    skipped_at = models.DateTimeField()
