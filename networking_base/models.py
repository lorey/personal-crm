from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import models
from pytz import UTC


class Contact(models.Model):
    name = models.CharField(max_length=50)
    frequency_in_days = models.IntegerField()
    user = models.ForeignKey(User, models.CASCADE)

    # contact details
    description = models.TextField(null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    linkedin_url = models.CharField(max_length=100, null=True, blank=True)
    twitter_username = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)

    def get_last_touchpoint(self):
        sorted_by_last = sorted(
            self.touchpoint_set.all(), key=lambda t: t.when, reverse=True
        )
        return next(iter(sorted_by_last), None)

    def get_urgency(self):
        now = datetime.now(tz=UTC)
        return (now - self.get_due_date()).days

    def get_due_date(self):
        last_touchpoint = self.get_last_touchpoint()
        if last_touchpoint:
            last_touchpoint_date = last_touchpoint.when
        else:
            now = datetime.now(tz=UTC)
            last_touchpoint_date = now - timedelta(days=365)
        return last_touchpoint_date + timedelta(days=self.frequency_in_days)

    def __str__(self):
        return self.name


class Touchpoint(models.Model):
    when = models.DateTimeField()
    contact = models.ForeignKey(Contact, models.CASCADE)

    def __str__(self):
        return self.when.isoformat()
