from django.contrib.auth.models import User
from django.test import TestCase

from networking_base.models import Contact

USER_PASSWORD = "secret"

USER_USERNAME = "peter"
USER_EMAIL = "peter@gmail.com"


class PageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(USER_USERNAME, USER_EMAIL, USER_PASSWORD)
        self.client.login(username=USER_USERNAME, password=USER_PASSWORD)

        self.contacts = []
        for i in range(5):
            c = Contact.objects.create(
                name=f"Contact {i}", frequency_in_days=i, user=self.user
            )
            self.contacts.append(c)

    def test_dashboard(self):
        resp = self.client.get("/app/")
        self.assertEqual(resp.status_code, 200)

    def test_contacts(self):
        resp = self.client.get("/app/contacts")
        self.assertEqual(resp.status_code, 200)

    def test_contact_detail(self):
        for contact in self.contacts:
            resp = self.client.get(f"/app/contacts/{contact.id}")
            self.assertEqual(resp.status_code, 200)

    def test_interactions(self):
        resp = self.client.get("/app/interactions")
        self.assertEqual(resp.status_code, 200)
