from difflib import SequenceMatcher

from django.contrib.auth.models import User
from django.core.management import BaseCommand

from networking_base.models import Contact, ContactDuplicate


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in User.objects.all():
            contacts = Contact.objects.filter(user=user).all()

            # delete old
            ContactDuplicate.objects.filter(contact__in=contacts).delete()
            ContactDuplicate.objects.filter(other_contact__in=contacts).delete()

            for contact in contacts:
                print(contact)

                similarities = {}
                other_contacts = filter(lambda c: c.id != contact.id, contacts)
                for other_contact in other_contacts:
                    similarity = get_contact_similarity(contact, other_contact)
                    if similarity > 0:
                        similarities[other_contact] = similarity

                # sort by similarity
                most_similar = sorted(
                    similarities.items(), key=lambda item: item[1], reverse=True
                )[:10]

                # create contact duplicate suggestions
                contact_duplicates = []
                for similar_contact, similarity in most_similar:
                    contact_duplicates.append(
                        ContactDuplicate(
                            contact=contact,
                            other_contact=similar_contact,
                            similarity=similarity,
                        )
                    )
                ContactDuplicate.objects.bulk_create(contact_duplicates)


def get_contact_similarity(c1, c2):
    similarity_email = SequenceMatcher(
        None, c1.name.split("@")[0], c2.name.split("@")[0]
    ).ratio()
    similarity_name = SequenceMatcher(None, c1.name, c2.name).ratio()
    return max(similarity_email, similarity_name)
