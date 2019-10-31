import datetime

from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.forms import ModelForm, ValidationError

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from django.utils.translation import gettext as _

from projects.models import Project, LegalEntity, Report

from tempus_dominus.widgets import DateTimePicker

from vote.models import UP, DOWN

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['type', 'name', 'description', 'published', 'legal_entity' ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['legal_entity'].queryset = LegalEntity.objects.filter(admin=user)

class ProjectDetails(generic.DetailView):
    model = Project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = datetime.datetime.now()
        context['reports'] = context['object'].report_set.filter(published_at__lte=now)
        context['unpublished_reports'] = context['object'].report_set.filter(published_at__gt=now)
        return context

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

class ReportForm(ModelForm):
    class Meta:
        model = Report
        fields = ['text', 'published_at']
        widgets = {
            'published_at': DateTimePicker(
                options={
                    'useCurrent': True,
                    'collapse': False,
                },
            )
        }

#TODO limit permissions
class ReportCreate(CreateView):
    model = Report
    form_class = ReportForm

    def form_valid(self, form):
        project_pk = self.kwargs['project']
        project = Project.objects.get(pk=project_pk)
        form.instance.project = project
        return super().form_valid(form)

class ReportUpdate(UpdateView):
    model = Report
    form_class = ReportForm

class ReportDelete(DeleteView):
    model = Report
    template_name = 'projects/project_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})

class ReportDetails(generic.DetailView):
    model = Report

    def get_context_data(self, **kwargs):
        print(kwargs)
        context = super().get_context_data(**kwargs)
        report = kwargs['object']
        context['votes_up'] = report.votes.count(UP)
        context['votes_down'] = report.votes.count(DOWN)
        vote = report.votes.get(self.request.user.pk)

        not_voted_classes = 'btn-light'
        voted_classes = 'btn-primary'
        vote_up_classes = not_voted_classes
        vote_down_classes = not_voted_classes

        if vote:
            if vote.action == UP:
                vote_up_classes = voted_classes
            else:
                vote_down_classes = voted_classes

        context['vote_up_classes'] = vote_up_classes
        context['vote_down_classes'] = vote_down_classes

        return context

def report_vote_up(request, pk):
    return report_vote(request, pk, UP)

def report_vote_down(request, pk):
    return report_vote(request, pk, DOWN)

@login_required
#TODO must be a subscriber to vote
def report_vote(request, pk, action):
    user = request.user
    report = get_object_or_404(Report, pk=pk)

    print(report.votes.count(UP))
    print(report.votes.count(DOWN))

    if report.votes.exists(user.pk, action=action):
        success = report.votes.delete(user.pk)
        if not success:
            messages.error(request, _('Could not delete vote'))

        else:
            messages.success(request, _('Deleted vote'))

    else:
        if action == UP:
            success = report.votes.up(user.pk)
        else:
            success = report.votes.down(user.pk)

        if not success:
            messages.error(request, _('Could not vote'))
        else:
            messages.success(request, _('Voted up') if action == UP else _('Voted down'))

    return redirect(report)
