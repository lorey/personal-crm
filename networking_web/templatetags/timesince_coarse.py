from django import template
from django.utils.timesince import timesince, timeuntil

register = template.Library()


@register.filter(needs_autoescape=True)
def timesince_coarse(date, autoescape=True):
    return timesince(date).split(",")[0]


@register.filter(needs_autoescape=True)
def timeuntil_coarse(date, autoescape=True):
    return timeuntil(date).split(",")[0]
