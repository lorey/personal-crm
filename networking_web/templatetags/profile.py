import hashlib
from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag
def profile_picture_url(contact, size=50):
    # defaults: http://en.gravatar.com/site/implement/images/

    # todo chose primary email or email with image tag
    email_o = contact.email_addresses.first()
    if email_o:
        email = email_o.email
    else:
        # use contact id instead of email for hashing
        # -> results in consistent hashes and thus images
        email = str(contact.id)

    gravatar_url = (
        "https://www.gravatar.com/avatar/"
        + hashlib.md5(email.lower().encode()).hexdigest()
        + "?"
    )
    gravatar_url += urlencode({"d": "robohash", "s": str(size)})
    return gravatar_url
