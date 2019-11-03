from django.utils import timezone

from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.forms import ModelForm, ValidationError

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from django.utils.translation import gettext as _

from projects.models import Project, LegalEntity, Report, MoneySupport, TimeSupport, User

from tempus_dominus.widgets import DateTimePicker, DatePicker

from vote.models import UP, DOWN

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'text', 'published', 'legal_entity', 'leva_needed', 'budget_until' ]
        widgets = {
            'budget_until': DatePicker(
                options={
                    'useCurrent': True,
                    'collapse': False,
                },
            )
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['legal_entity'].queryset = LegalEntity.objects.filter(admin=user)

class ProjectDetails(generic.DetailView):
    model = Project

class ProjectCreate(CreateView):
    model = Project
    form_class = ProjectForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['type'] = self.kwargs['type']

        return context

    def form_valid(self, form):
        user = self.request.user
        project = form.instance
        legal_entity = project.legal_entity
        if legal_entity.admin != user:
            form.add_error('legal_entity', 'You must be the admin of the legal entity. Admin for %s is %s' % (legal_entity, legal_entity.admin))
            return super().form_invalid(form)

        project.type = self.request.kwargs['type']

        return super().form_valid(form)

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
    fields = ['name', 'bulstat', 'email', 'phone', 'payment']

    def form_valid(self, form):
        user = self.request.user
        form.instance.admin = user
        return super().form_valid(form)

class LegalEntityUpdate(UpdateView):
    model = LegalEntity
    fields = ['name', 'bulstat', 'email', 'phone', 'admin', 'payment']

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

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['member'] = self.request.user.member_of(context['object'].pk)
        return context


class LegalEntityList(generic.ListView):
    model = LegalEntity

@login_required
def legal_join(request, pk):
    user = request.user
    
    if user.member_of(pk):
        messages.info(request, _("You are already a member"))

    #TODO ask legal entity's admin instead of directly adding

    else:
        legal_entity = get_object_or_404(LegalEntity, pk=pk)
        user.legal_entities.add(legal_entity)
        messages.success(request, _("Success"))

    return redirect('projects:legal_details', pk)

@login_required
def legal_exit(request, pk):
    user = request.user
    
    if not user.member_of(pk):
        messages.info(request, _("Not a member"))
    else:
        legal_entity = user.legal_entities.filter(pk=pk).first()
        if legal_entity.admin == user:
            messages.error(request, _("You are the admin"))

        else:
            user.legal_entities.remove(legal_entity)
            messages.success(request, _("Exited"))

    return redirect('projects:legal_details', pk)

class ReportForm(ModelForm):
    class Meta:
        model = Report
        fields = ['name', 'text', 'published_at']
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

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        context['project'] = self.project
        return context

    def form_valid(self, form):
        form.instance.project = self.project
        return super().form_valid(form)

class ReportUpdate(UpdateView):
    model = Report
    form_class = ReportForm

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

class ReportDelete(DeleteView):
    model = Report
    template_name = 'projects/project_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})

class ReportDetails(generic.DetailView):
    model = Report

    def get_context_data(self, **kwargs):
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

class ReportList(generic.ListView):
    model = Report

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        project_pk = self.kwargs['project']
        context['project'] = get_object_or_404(Project, pk=project_pk)

        context['reports'] = Report.objects.filter(project_id=project_pk, published_at__lte=now)
        context['unpublished_reports'] = Report.objects.filter(project_id=project_pk, published_at__gt=now)

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

class MoneySupportCreate(CreateView):
    model = MoneySupport
    fields = ['leva']

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        context['project'] = self.project
        return context

    def form_valid(self, form):
        form.instance.project = self.project

        user = self.request.user
        form.instance.user = user

        return super().form_valid(form)

#TODO only allow if support is not accepted
class MoneySupportUpdate(UpdateView):
    model = MoneySupport
    fields = ['leva']

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

class MoneySupportDetails(generic.DetailView):
    model = MoneySupport
    template_name = 'projects/support_detail.html'

#TODO only allow if support is not accepted
class SupportDelete(DeleteView):
    model = MoneySupport
    template_name = 'projects/project_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})

def report_vote(request, pk, action):
    user = request.user
    report = get_object_or_404(Report, pk=pk)

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

def support_accept(request, pk, type):
    return support_change_accept(request, pk, type, True)

def support_decline(request, pk, type):
    return support_change_accept(request, pk, type, False)

def support_change_accept(request, pk, type, accepted):
    if type in ['money', 'm']:
        support = get_object_or_404(MoneySupport, pk=pk)
    else:
        support = get_object_or_404(TimeSupport, pk=pk)

    if support.accepted == accepted:
        messages.info(request, _('Support already accepted') if accepted else _('Support already declined'))
    else:
        support.accepted = accepted
        if accepted:
            support.accepted_at = timezone.now()
        else:
            support.accepted_at = None
        support.save()

        messages.success(request, _('Support accepted') if accepted else _('Support declined'))

    return redirect(support)

def support_delivered(request, pk, type):
    if type in ['money', 'm']:
        support = get_object_or_404(MoneySupport, pk=pk)
    else:
        support = get_object_or_404(TimeSupport, pk=pk)

    if support.delivered:
        messages.info(request, _('Support already marked as delivered'))
    else:
        support.delivered = True
        support.delivered_at = timezone.now()
        support.save()

        messages.success(request, _('Support marked as delivered'))

    return redirect(support)

def support_list(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    money_support_list = MoneySupport.objects.filter(project_id=project_id).all()
    time_support_list = TimeSupport.objects.filter(project_id=project_id).all()
    return render(request, 'projects/support_list.html', context={
        'money_support_list': money_support_list,
        'time_support_list': time_support_list,
        'project': project
        }
    )

def support_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return render(request, 'projects/support_create.html', context={
        'project': project,
        }
    )

def support_details(request, pk):
    support = MoneySupport.objects.get(pk=pk)
    if not support:
        support = TimeSupport.objects.get(pk=pk)

    return redirect(support)

class TimeSupportForm(ModelForm):
    class Meta:
        model = TimeSupport
        fields = ['start_date', 'end_date', 'note']
        widgets = {
            'start_date': DatePicker(
                options={
                    'useCurrent': True,
                    'collapse': False,
                },
            ),
            'end_date': DatePicker(
                options={
                    'useCurrent': True,
                    'collapse': False,
                },
            ),
        }

class TimeSupportCreate(CreateView):
    model = TimeSupport
    form_class = TimeSupportForm
    template_name = 'projects/project_form.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        context['project'] = self.project
        return context

    def form_valid(self, form):
        form.instance.project = self.project

        user = self.request.user
        form.instance.user = user

        return super().form_valid(form)

#TODO only allow if support is not accepted
class TimeSupportUpdate(UpdateView):
    model = TimeSupport
    fields = ['leva']

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

class TimeSupportDetails(generic.DetailView):
    model = TimeSupport
    template_name = 'projects/support_detail.html'

def user_support_list(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    money_supports = MoneySupport.objects.filter(user=user).all()
    time_supports = TimeSupport.objects.filter(user=user).all()

    return render(request, 'projects/user_support_list.html', context={
        'account': user,
        'money_support_list': money_supports,
        'time_support_list': time_supports
        }
    )

def user_vote_list(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    votes_up = Report.votes.all(user_id, UP) 
    votes_down = Report.votes.all(user_id, DOWN)

    supported_projects = set()
    money_supported = user.moneysupport_set.all()
    time_supported = user.timesupport_set.all()

    awaiting_list = []
    #TODO use stream framework for this
    #for m in money_supported:
    #    supported_projects.add(m.project)

    #for t in time_supported:
    #    supported_projects.add(t.project)

    #for p in supported_projects:
    #    awaiting_list.extend(p.report_set.filter())

    return render(request, 'projects/user_vote_list.html', context={
        'account': user,
        'awaiting_list': awaiting_list,
        'votes_up': votes_up,
        'votes_down': votes_down
        }
    )

