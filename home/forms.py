from django.utils.safestring import mark_safe
from allauth.account.forms import SignupForm
from django import forms

from django.utils.translation import gettext as _

from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as translate_lazy

mark_safe_lazy = lazy(mark_safe)

class NamesSignupForm(SignupForm):

    field_order = ['first_name', 'last_name', 'email', 'password1', 'accept_tos']

    #TODO add validators - no space allowed
    first_name = forms.CharField(
        label=_("First Name"),
        max_length=30)
    last_name = forms.CharField(
        label=_("Last Name"),
        max_length=30)
    accept_tos = forms.BooleanField(
        label=mark_safe_lazy(translate_lazy('Accept <a href="/условия-за-ползване">Terms of Service</a>')))

    def save(self, request):

        user = super(NamesSignupForm, self).save(request)

        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']

        return user
