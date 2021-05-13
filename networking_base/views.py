import pandas as pd
from dateutil.parser import parse
from django.core.exceptions import MultipleObjectsReturned

from networking_base.models import Contact, Touchpoint


def create_contacts_from_file_handle(file, owner, col_email, col_name):
    df = pd.read_csv(file)

    df_clean = pd.DataFrame()
    df_clean["name"] = df[col_name]
    df_clean["email"] = df[col_email]
    df_clean["owner_id"] = owner.id
    df_clean["frequency"] = 7

    return create_contacts_from_df(df_clean)


def create_contacts_from_df(df):
    data = df.to_dict(orient="rows")
    contacts = [
        Contact(
            name=d["name"] if not pd.isna(d["name"]) else d["email"],
            email=d["email"] if not pd.isna(d["email"]) else None,
            user_id=d["owner_id"],
            frequency_in_days=d["frequency"],
        )
        for d in data
    ]
    return contacts


def create_contacts_from_trello(trello_json, user, frequency_default=7):
    labels_by_id = {label["id"]: label for label in trello_json["labels"]}

    contacts = []
    for trello_card in trello_json["cards"]:
        if not trello_card["closed"]:
            contact = create_contact_from_trello_card(
                trello_card, user, frequency_default, labels_by_id
            )
            contacts.append(contact)
    return contacts


def create_contact_from_trello_card(
    card: dict, user, frequency_default=7, labels_by_id=None
):
    if not labels_by_id:
        labels_by_id = {}

    labels_card = [labels_by_id[label_id] for label_id in card["idLabels"]]
    card_description = make_card_description(card, labels_card)

    try:
        contact, was_created = Contact.objects.get_or_create(
            name=card["name"],
            user=user,
            defaults={
                "frequency_in_days": frequency_default,
                "description": card_description,
            },
        )
    except MultipleObjectsReturned:
        # user might have several people with the same name...
        # -> just ignore this record
        return None

    # create activity based on trello's last activity
    last_activity_raw = card["dateLastActivity"]
    last_activity = parse(last_activity_raw) if last_activity_raw else None
    if was_created and last_activity:
        # get or create to avoid duplicates on multiple imports
        Touchpoint.objects.get_or_create(when=last_activity, contact=contact)

    return contact


def make_card_description(card, labels_card):
    content_parts = []

    # add regular description
    if card["desc"]:
        content_parts.append(card["desc"])

    # add one label per row
    card_label_desc = [
        "Label: {name} ({color})".format(**label) for label in labels_card
    ]
    if card_label_desc:
        content_parts.append("\n".join(card_label_desc))

    # add import statement
    content_parts.append("Imported from Trello: {}".format(card["url"]))

    # merge all contents
    card_description = "\n\n".join(content_parts)

    return card_description
