from django import template
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from vote.models import UP, DOWN
from ..models import Support

register = template.Library()

@register.simple_tag
def member_of(user, community_pk):
    return user.is_authenticated and user.member_of(community_pk)

@register.simple_tag
def vote_exists(report, user_pk):
    return report.votes.exists(user_pk, action=UP) or report.votes.exists(user_pk, action=DOWN)

@register.simple_tag
def format_answer(answer):
    type = answer.question.prototype.type
    if type in ['CharField', 'TextField']:
        return answer.answer
    #TODO
    if type == 'FileField':
        return answer.answer
    if type == 'ChoiceField':
        return [gettext_lazy('Yes'), gettext_lazy('No')][int(answer.answer)-1]
    if type == 'Necessities':
        return ""

    return "not implemented"

@register.filter
def leva(value):
    if value == 0:
        return '0 ' + _('lv')

    if value is None:
        return _("unknown")

    return "%.2f " % value + _('lv') 


STATUS_COLOR = {
    Support.STATUS.review: 'warning',
    Support.STATUS.delivered: 'success',
    Support.STATUS.accepted: 'default',
    Support.STATUS.declined: 'danger',
    Support.STATUS.expired: 'light',
    }

@register.filter
def status_color(status):
    return STATUS_COLOR.get(status, 'default')

@register.filter
def status_text(status):
    return gettext_lazy(status)
