from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import UpdateView
from projects.models import User

# Create your views here.

class UserUpdate(UpdateView):
    model = User
    fields = ['first_name', 'last_name']
    success_url = '/accounts/profile/'

def account(request, pk=None):
    if pk:
        account = get_object_or_404(User, pk=pk)
    else:
        account = request.user 
    return render(request, 'home/account.html', { 'account': account} )
