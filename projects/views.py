from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.forms import ModelForm, ValidationError

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from projects.models import Project, LegalEntity

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['type', 'name', 'description', 'published', 'legal_entity' ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['legal_entity'].queryset = LegalEntity.objects.filter(admin=user)

class Details(generic.DetailView):
    model = Project

class ProjectCreate(CreateView):
    model = Project
    form_class = ProjectForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

class ProjectUpdate(UpdateView):
    model = Project
    form_class = ProjectForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        legal_entity = form.instance.legal_entity
        if legal_entity.admin != user:
            form.add_error('legal_entity', 'You must be the admin of the legal entity. Admin for %s is %s' % (legal_entity, legal_entity.admin))
            return super().form_invalid(form)
        return super().form_valid(form)

class ProjectDelete(DeleteView):
    model = Project
    success_url = '/'

class LegalEntityCreate(CreateView):
    model = LegalEntity
    fields = ['name', 'bulstat', 'email', 'phone']

    def form_valid(self, form):
        user = self.request.user
        form.instance.admin = user
        return super().form_valid(form)

class LegalEntityUpdate(UpdateView):
    model = LegalEntity
    fields = ['name', 'bulstat', 'email', 'phone', 'admin']

    def form_valid(self, form):
        admin = form.instance.admin
        if not admin.legal_entities.filter(pk=form.instance.pk).exists():
            admin.legal_entities.add(form.instance)

        return super().form_valid(form)

class LegalEntityDelete(DeleteView):
    model = LegalEntity
    success_url = reverse_lazy('projects:legal_list')

class LegalEntityDetails(generic.DetailView):
    model = LegalEntity

class LegalEntityList(generic.ListView):
    model = LegalEntity

@login_required
def legal_join(request, pk):
    user = request.user
    
    if user.legal_entities.filter(pk=pk).exists():
        return HttpResponse("noop", status=300) 

    #TODO ask legal entity's admin instead of directly adding

    legal_entity = get_object_or_404(LegalEntity, pk=pk)
    user.legal_entities.add(legal_entity)

    return HttpResponse("ok")

@login_required
def legal_exit(request, pk):
    user = request.user
    
    legal_entity =  user.legal_entities.filter(pk=pk).first()

    if not legal_entity:
        return HttpResponse("noop", status=300) 

    if legal_entity.admin == user:
        return HttpResponse("you are the admin", status=400) 

    user.legal_entities.remove(legal_entity)

    return HttpResponse("ok")
