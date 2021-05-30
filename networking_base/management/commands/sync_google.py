import logging
import re
import typing
from datetime import date, datetime
from enum import Enum

import google.oauth2.credentials
import pytz
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from googleapiclient.discovery import build

from networking_base.models import (
    GoogleCalendarEvent,
    GoogleEmail,
    Interaction,
    clean_email,
    get_or_create_contact_email,
)

# todo map emails to names in order to create contacts

REGEX_EMAIL = r"[A-z0-9_.+-]+@[A-z0-9_.-]+\.[A-z]+"
EMAIL_TITLE_DEFAULT = "Email without subject"


class HeaderParsingException(Exception):
    pass


def extract_emails(header_str):
    matches = re.findall(REGEX_EMAIL, header_str)
    if not matches:
        raise HeaderParsingException(f"parsing failed: {header_str}")

    return list({clean_email(m) for m in matches})


class EmailDirection(Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    UNKNOWN = None


class GmailEmailAdapter:
    """
    Representation of a gmail email.
    """

    def __init__(self, data):
        self._data = data

    def get_id(self):
        return self._data["id"]

    def get_header_values_by_name(self):
        return {h["name"]: h["value"] for h in self._data["payload"]["headers"]}

    def get_to_emails(self):
        to_ = self.get_header_values_by_name().get("To")
        if not to_:
            return []

        return extract_emails(to_)

    def get_from_email(self):
        from_ = self.get_header_values_by_name()["From"]
        emails = extract_emails(from_)
        if len(emails) != 1:
            logging.warning(f'Parsing returned weird "from": {from_=} {emails=}')
        return emails[0]

    def get_subject(self):
        return self.get_header_values_by_name().get("Subject")

    def get_snippet(self):
        return self._data["snippet"]

    def get_direction(self, user_emails) -> EmailDirection:
        is_in_from = any(
            user_email == self.get_from_email() for user_email in user_emails
        )
        is_in_to = any(user_email in self.get_to_emails() for user_email in user_emails)

        if is_in_from and is_in_to:
            # user sends themselves email
            return EmailDirection.UNKNOWN

        if is_in_from:
            return EmailDirection.OUTGOING

        if is_in_to:
            return EmailDirection.INCOMING

        return EmailDirection.UNKNOWN

    def is_outgoing(self, user_emails):
        return self.get_direction(user_emails) == EmailDirection.OUTGOING

    def get_date(self):
        g_timestamp = int(self._data["internalDate"]) / 1000
        return datetime.fromtimestamp(g_timestamp).astimezone(pytz.UTC)

    def print(self, user_emails):
        print(f"from: {self.get_from_email()}")
        print(f"to: {self.get_to_emails()}")
        print(f"-> {self.get_direction(user_emails)}")
        print(f"subject: {self.get_subject()}")
        print(f"snippet: {self.get_snippet()}")
        print(f"on: {self.get_date()}")


class GoogleCalendarEventStatus(Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class GoogleCalendarEventAdapter:
    def __init__(self, data):
        assert data["kind"] == "calendar#event"
        self._data = data

    def get_id(self) -> str:
        return self._data["id"]

    def get_status(self) -> GoogleCalendarEventStatus:
        """If the event is confirmed."""
        return GoogleCalendarEventStatus(self._data["status"])

    def get_url(self):
        return self._data["htmlLink"]

    def get_summary(self):
        return self._data["summary"]

    def get_start(self):
        return self._get_date_or_datetime(self._data["start"])

    def get_end(self):
        return self._get_date_or_datetime(self._data["end"])

    def _get_date_or_datetime(self, data) -> typing.Union[datetime, date]:
        if "dateTime" in data:
            return datetime.strptime(data["dateTime"], "%Y-%m-%dT%H:%M:%S%z")
        return datetime.strptime(data["date"], "%Y-%m-%d").date()

    def print(self):
        print(self.get_url())
        print(self.get_summary())
        print(self.get_status())
        print(f"{self.get_start()} - {self.get_end()}")
        print(self.get_attendees())

    def get_attendees(self):
        return self._data.get("attendees", [])


class Command(BaseCommand):
    def handle(self, *args, **options):
        # fetch calendar and gmail for all users
        for user in User.objects.all():
            self.stdout.write(f"syncing {user}")
            gus = GoogleUserSync(user)
            gus.sync()


class GoogleUserSync:
    def __init__(self, user):
        self.user = user
        self.social_account = None

        self.user_emails = {
            clean_email(sa_email_address.email)
            for sa_email_address in EmailAddress.objects.filter(user=self.user).all()
        }

    def sync(self):
        # get social account
        self.social_account = SocialAccount.objects.get(
            user=self.user, provider="google"
        )

        self.sync_calendar()
        self.sync_gmail()
        self.update_interactions()

    def update_interactions(self):
        # updates need to be performed each time as mapped contacts could have changed

        # update emails
        google_emails = GoogleEmail.objects.filter(
            social_account=self.social_account
        ).all()
        for google_email in google_emails:
            try:
                update_email_interaction(google_email, self.user_emails)
            except HeaderParsingException:
                logging.exception("parsing email failed")

        # update interactions for all calendar events
        google_events = GoogleCalendarEvent.objects.filter(
            social_account=self.social_account
        ).all()
        for google_event in google_events:
            update_calendar_interaction(google_event, self.user_emails)

    def sync_calendar(self):
        social_token = SocialToken.objects.get(account=self.social_account)
        credentials = self._make_credentials(social_token)
        service = build("calendar", "v3", credentials=credentials)

        request = service.events().list(calendarId="primary", maxResults=2500)
        while request:
            response = request.execute()
            for item in response["items"]:
                gcal_event, was_created = GoogleCalendarEvent.objects.get_or_create(
                    google_calendar_id=item["id"],
                    defaults={"data": item, "social_account": self.social_account},
                )
                if not was_created:
                    # calendar events can change, so needs to be updated
                    gcal_event.data = item
                    gcal_event.save()

            # define next request
            request = service.events().list_next(
                previous_request=request, previous_response=response
            )

    def _make_credentials(self, social_token: SocialToken):
        social_app = SocialApp.objects.get(provider="google")
        if not social_token.token_secret:
            logging.warning(
                f"refresh token (token secret) missing for {self.social_account.user}, needs to re-add app"
            )
        credentials = google.oauth2.credentials.Credentials(
            social_token.token,
            refresh_token=social_token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=social_app.client_id,
            client_secret=social_app.secret,
        )
        return credentials

    def sync_gmail(self):
        social_token = SocialToken.objects.get(account=self.social_account)
        credentials = self._make_credentials(social_token)
        service = build("gmail", "v1", credentials=credentials)

        request = service.users().messages().list(userId="me", maxResults=5000)
        while request:
            token_old = credentials.token
            response = request.execute()
            token_new = credentials.token

            # update social token
            if token_old != token_new:
                social_token.token = credentials.token
                social_token.expires_at = pytz.utc.localize(credentials.expiry)
                social_token.save()
                logging.warning("credentials changed: updated")

            for result in response["messages"]:
                if (
                    GoogleEmail.objects.filter(gmail_message_id=result["id"]).count()
                    == 0
                ):
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=result["id"], format="metadata")
                        .execute()
                    )

                    GoogleEmail.objects.get_or_create(
                        gmail_message_id=msg["id"],
                        defaults={"data": msg, "social_account": self.social_account},
                    )

            # define next request
            request = (
                service.users()
                .messages()
                .list_next(previous_request=request, previous_response=response)
            )


def update_email_interaction(
    google_email: GoogleEmail, ignore_emails=()
) -> Interaction:
    user = google_email.social_account.user

    # make data accessible
    google_email_adapter = GmailEmailAdapter(google_email.data)

    # create interaction
    interaction = google_email.interaction
    if not interaction:
        interaction = Interaction()

    interaction.title = google_email_adapter.get_subject() or EMAIL_TITLE_DEFAULT
    interaction.description = google_email_adapter.get_snippet()
    interaction.was_at = google_email_adapter.get_date()
    interaction.type_id = None
    interaction.user = user
    interaction.save()

    # remeber created interaction
    google_email.interaction = interaction
    google_email.save()

    # connect contacts
    emails_raw = set(google_email_adapter.get_to_emails()) | {
        google_email_adapter.get_from_email()
    }
    email_addresses = [
        get_or_create_contact_email(email, user)
        for email in emails_raw
        if email not in ignore_emails
    ]
    interaction.contacts.set({ea.contact for ea in email_addresses})

    return interaction


def update_calendar_interaction(
    event: GoogleCalendarEvent, ignore_emails=()
) -> typing.Optional[Interaction]:
    """
    Takes a google calendar event and creates/updates/deletes the corresponding interaction.
    :param ignore_emails: ignored emails
    :param event: calendar event
    """
    user = event.social_account.user

    event_adapter = GoogleCalendarEventAdapter(event.data)

    needs_interaction = (
        # event must be confirmed
        event_adapter.get_status() == GoogleCalendarEventStatus.CONFIRMED
        # event has attendees
        and event_adapter.get_attendees()
    )

    if needs_interaction:
        # create interaction
        interaction = event.interaction
        if not interaction:
            interaction = Interaction()

        # update interaction
        event_end = event_adapter.get_end()
        event_end_datetime = (
            # if datetime, use datetime
            event_end
            if isinstance(event_end, datetime)
            # make latest possible datetime, if date
            else datetime.combine(event_end, datetime.max.time())
        )

        interaction.title = event_adapter.get_summary()
        interaction.description = "Google Calendar Event"
        interaction.was_at = event_end_datetime.astimezone()
        interaction.type_id = None
        interaction.user = user
        interaction.save()

        # remember interaction in event
        event.interaction = interaction
        event.save()

        # connect all invitees
        emails_raw = {attendee["email"] for attendee in event_adapter.get_attendees()}
        email_addresses = [
            get_or_create_contact_email(email, user)
            for email in emails_raw
            if email not in ignore_emails
        ]
        interaction.contacts.set({ea.contact for ea in email_addresses})

        return interaction
    else:
        # no interaction object desired:
        # delete the interaction if it still exists
        if event.interaction:
            event.interaction.delete()
        return None
