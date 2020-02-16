import pandas as pd

from networking_base.models import Contact


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
