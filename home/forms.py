from allauth.account.forms import SignupForm
from django import forms

from django.utils.translation import gettext as _

class NamesSignupForm(SignupForm):

    field_order = ['first_name', 'last_name', 'email', 'password', 'accept_tos']

    #TODO add validators - no space allowed
    first_name = forms.CharField(
        label=_("First Name"),
        max_length=30)
    last_name = forms.CharField(
        label=_("Last Name"),
        max_length=30)
    accept_tos = forms.BooleanField(
        label=_("Accept Terms of Service"))

    def save(self, request):

        user = super(NamesSignupForm, self).save(request)

        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']

        return user
