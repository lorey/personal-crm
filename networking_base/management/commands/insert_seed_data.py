import random
from datetime import datetime, timedelta

from django.core.management import BaseCommand
from pytz import UTC

from networking_base.models import Contact, Touchpoint


class Command(BaseCommand):
    def handle(self, *args, **options):
        firstnames = ["Peter", "Barbara", "Klaus", "Karl", "Ferdinand", "Otto"]
        lastnames = ["Müller", "Meyer", "Merkel", "Duck", "Gamma"]
        for i in range(100):
            name = " ".join([random.choice(firstnames), random.choice(lastnames)])
            contact = Contact.objects.create(
                name=name, frequency_in_days=random.randrange(1, 100)
            )

            for j in range(10, 100):
                date_random = datetime.now(tz=UTC) - timedelta(
                    days=random.randrange(1, 365)
                )
                Touchpoint.objects.create(when=date_random, contact=contact)
