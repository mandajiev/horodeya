from django import template
from django.utils.translation import gettext as _

from vote.models import UP, DOWN

register = template.Library()

@register.simple_tag
def vote_exists(report, user_pk):
    return report.votes.exists(user_pk, action=UP) or report.votes.exists(user_pk, action=DOWN)

@register.filter
def leva(value):
    if value:
        return "%.2f " % value + _('lv') 
    else:
        return _("unknown")

