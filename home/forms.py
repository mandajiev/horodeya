from allauth.account.forms import SignupForm
from django import forms

class NamesSignupForm(SignupForm):

    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    accept_tos = forms.BooleanField()

    def save(self, request):

        user = super(NamesSignupForm, self).save(request)

        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']

        return user
