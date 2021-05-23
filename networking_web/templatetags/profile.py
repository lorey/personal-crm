import hashlib
from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag
def profile_picture_url(contact, size=50):
    # defaults: http://en.gravatar.com/site/implement/images/
    email = contact.emails.first().email
    gravatar_url = (
        "https://www.gravatar.com/avatar/"
        + hashlib.md5(email.lower().encode()).hexdigest()
        + "?"
    )
    gravatar_url += urlencode({"d": "robohash", "s": str(size)})
    return gravatar_url
