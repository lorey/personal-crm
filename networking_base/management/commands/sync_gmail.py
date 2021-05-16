import logging
import re
from datetime import datetime
from enum import Enum

import google.oauth2.credentials
import pytz
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from googleapiclient.discovery import build

# todo map emails to names iot create contacts
from networking_base.models import Contact, EmailAddress, EmailInteraction


def extract_email(header_str):
    matches = re.findall(r"[A-z0-9_.+-]+@[A-z0-9_.-]+\.[A-z]+", header_str)
    if not matches:
        raise RuntimeError(f"email not found: {header_str}")

    return matches[0].lower()


class EmailDirection(Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    UNKNOWN = None


class GmailEmail:
    def __init__(self, data):
        self._data = data

    def get_id(self):
        return self._data["id"]

    def get_header_values_by_name(self):
        return {h["name"]: h["value"] for h in self._data["payload"]["headers"]}

    def get_to_emails(self):
        to_raw = self.get_header_values_by_name().get("To")
        if not to_raw:
            return []

        return list(map(extract_email, to_raw.split(",")))

    def get_from_email(self):
        return extract_email(self.get_header_values_by_name()["From"])

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


def get_or_create_contact_email(email, user):
    email_clean = email.lower()
    ea = EmailAddress.objects.filter(email=email_clean, contact__user=user).first()
    if not ea:
        # email does not exist
        # -> create contact (dummy) and email
        contact = Contact.objects.create(user=user, name=email, frequency_in_days=365)
        ea = EmailAddress.objects.create(email=email_clean, contact=contact)
    return ea


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in User.objects.all():
            social_account = SocialAccount.objects.get(user=user)
            user_email = social_account.extra_data["email"].lower()
            user_emails = [user_email]

            social_token = SocialToken.objects.get(account=social_account)
            social_app = SocialApp.objects.get(provider="google")
            credentials = google.oauth2.credentials.Credentials(
                social_token.token,
                refresh_token=social_token.token_secret,
                # todo
                token_uri="https://oauth2.googleapis.com/token",
                client_id=social_app.client_id,
                client_secret=social_app.secret,
            )
            service = build("gmail", "v1", credentials=credentials)

            request = service.users().messages().list(userId="me")
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

                # print(response, "\n")

                for result in response["messages"]:
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=result["id"])
                        .execute()
                    )

                    try:
                        gmail_email = GmailEmail(msg)
                        gmail_email.print(user_emails)
                        print()

                        if gmail_email.is_outgoing(user_emails):
                            for to_email in gmail_email.get_to_emails():
                                contact_email = get_or_create_contact_email(
                                    to_email, user
                                )

                                EmailInteraction.objects.get_or_create(
                                    gmail_message_id=gmail_email.get_id(),
                                    contact=contact_email.contact,
                                    defaults={
                                        "title": gmail_email.get_subject() or "-",
                                        "description": gmail_email.get_snippet() or "-",
                                        "was_at": gmail_email.get_date(),
                                    },
                                )
                    except RuntimeError:
                        logging.exception("parsing failed")

                # define next request
                request = (
                    service.users()
                    .messages()
                    .list_next(previous_request=request, previous_response=response)
                )
