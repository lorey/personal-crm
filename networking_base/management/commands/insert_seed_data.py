import random
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.management import BaseCommand
from pytz import UTC

from networking_base.models import Contact, Interaction


class Command(BaseCommand):
    def handle(self, *args, **options):
        firstnames = ["Peter", "Barbara", "Klaus", "Karl", "Ferdinand", "Otto"]
        lastnames = ["Müller", "Meyer", "Merkel", "Duck", "Gamma"]
        lastnames_double = [
            "-".join([l1, l2]) for l1 in lastnames for l2 in lastnames if l1 != l2
        ]
        lastnames_full = lastnames + lastnames_double

        for u in User.objects.all():
            for i in range(100):
                name = " ".join(
                    [random.choice(firstnames), random.choice(lastnames_full)]
                )
                contact = Contact.objects.create(
                    name=name, frequency_in_days=random.randrange(7, 30), user=u
                )

                for j in range(0, 100):
                    date_random = datetime.now(tz=UTC) - timedelta(
                        days=random.randrange(1, 365)
                    )
                    Interaction.objects.create(
                        was_at=date_random,
                        contact=contact,
                        title="Interaction",
                        description="Talked",
                    )
