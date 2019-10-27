from django.shortcuts import render
from django.views.generic.edit import UpdateView
from django.contrib.auth.models import User

# Create your views here.

class UserUpdate(UpdateView):
    model = User
    fields = ['first_name', 'last_name']
    success_url = '/accounts/profile/'

def account(request):
    return render(request, 'home/account.html')
