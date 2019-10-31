from django import template

from vote.models import UP, DOWN

register = template.Library()

@register.simple_tag
def vote_exists(report, user_pk):
    return report.votes.exists(user_pk, action=UP) or report.votes.exists(user_pk, action=DOWN)

