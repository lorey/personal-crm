from django.contrib.auth.models import User
from django.test import TestCase

USER_PASSWORD = "secret"

USER_USERNAME = "peter"
USER_EMAIL = "peter@gmail.com"


class PageTest(TestCase):
    def setUp(self):
        User.objects.create_user(USER_USERNAME, USER_EMAIL, USER_PASSWORD)
        self.client.login(username=USER_USERNAME, password=USER_PASSWORD)

    def test_dashboard(self):
        resp = self.client.get("/app/")
        self.assertEqual(resp.status_code, 200)

    def test_contacts(self):
        resp = self.client.get("/app/contacts")
        self.assertEqual(resp.status_code, 200)

    def test_interactions(self):
        resp = self.client.get("/app/interactions")
        self.assertEqual(resp.status_code, 200)
