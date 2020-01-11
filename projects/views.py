from django.utils import timezone

from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.utils.html import format_html
from django.forms import ModelForm, ValidationError, inlineformset_factory, modelformset_factory

from django import forms

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from django.utils.translation import gettext as _

from rules.contrib.views import AutoPermissionRequiredMixin, permission_required, objectgetter

from projects.models import Project, LegalEntity, Report, MoneySupport, TimeSupport, User, Announcement, TimeNecessity, ThingNecessity

from tempus_dominus.widgets import DateTimePicker, DatePicker

from vote.models import UP, DOWN

from dal import autocomplete

from stream_django.feed_manager import feed_manager
from stream_django.enrich import Enrich

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'text', 'published', 'legal_entity', 'end_date' ]
        widgets = {
            'end_date': DatePicker(
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

class AnnouncementForm(ModelForm):
    class Meta:
        model = Announcement
        fields = ['text']
        widgets = {
          'text': forms.Textarea(attrs={'rows': 2}),
        }

TimeNecessityFormset = inlineformset_factory(
        Project,
        TimeNecessity,
        fields=['name', 'description', 'count', 'price', 'start_date', 'end_date' ],
        widgets={
            'count': forms.TextInput({
                'style': 'width: 60px'
                }
            ),
            'price': forms.TextInput({
                'style': 'width: 60px'
                }
            ),
            'description': forms.Textarea({
                'rows': 1,
                'cols': 30
                }
            ),
            'start_date': DatePicker(
                attrs={
                    'style': 'width:120px'
                    },
                options={
                    'useCurrent': True,
                    'collapse': False,
                },
            ),
            'end_date': DatePicker(
                attrs={
                    'style': 'width:120px'
                    },
                options={
                    'useCurrent': True,
                    'collapse': False,
                },
            )
        },
        extra=1) 

ThingNecessityFormset = inlineformset_factory(
        Project,
        ThingNecessity,
        fields=['name', 'description', 'count', 'price' ],
        widgets={
            'count': forms.TextInput({
                'style': 'width: 60px'
                }
            ),
            'price': forms.TextInput({
                'style': 'width: 60px'
                }
            ),
            'description': forms.Textarea({
                'rows': 1,
                }
            ),
        },
        extra=1) 

def thing_necessity_update(request, project_id):
    return necessity_update(request, project_id, 'thing')

def time_necessity_update(request, project_id):
    return necessity_update(request, project_id, 'time')

def necessity_update(request, project_id, type):
    cls = TimeNecessityFormset if type == 'time' else ThingNecessityFormset
    template_name = 'projects/necessity_form.html'
    project = get_object_or_404(Project, pk=project_id)

    if request.method == 'GET':
        # we don't want to display the already saved model instances
        formset = cls(instance=project)

    elif request.method == 'POST':
        formset = cls(request.POST, instance=project)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data.get('DELETE'):
                    form.instance.delete()

                elif form.cleaned_data.get('name'):
                    form.instance.project = project
                    form.save()
            if 'add-row' in request.POST:
                    
                formset = cls(instance=project) # за да добави празен ред
            else:
                return redirect(project)

    return render(request, 'projects/necessity_form.html', {
        'formset': formset,
        'project': project,
        'type': type
    })


class ProjectDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = Project

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        feed = feed_manager.get_feed('project', context['object'].id)
        enricher = Enrich()
        try:
            timeline = enricher.enrich_activities(feed.get(limit=25)['results'])
            context['timeline'] = timeline
        except ConnectionError:
            context['timeline'] = None 

        context['announcement_form'] = AnnouncementForm()

        return context

class ProjectCreate(AutoPermissionRequiredMixin, CreateView):
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

class ProjectUpdate(AutoPermissionRequiredMixin, UpdateView):
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

class ProjectDelete(AutoPermissionRequiredMixin, DeleteView):
    model = Project
    success_url = '/'

class LegalEntityCreate(AutoPermissionRequiredMixin, CreateView):
    model = LegalEntity
    fields = ['name', 'bulstat', 'email', 'phone', 'payment']

    def form_valid(self, form):
        user = self.request.user
        form.instance.admin = user
        return super().form_valid(form)

class LegalEntityUpdate(AutoPermissionRequiredMixin, UpdateView):
    model = LegalEntity
    fields = ['name', 'bulstat', 'email', 'phone', 'admin', 'payment']

    def form_valid(self, form):
        admin = form.instance.admin
        if not admin.legal_entities.filter(pk=form.instance.pk).exists():
            admin.legal_entities.add(form.instance)

        return super().form_valid(form)

class LegalEntityDelete(AutoPermissionRequiredMixin, DeleteView):
    model = LegalEntity
    success_url = reverse_lazy('projects:legal_list')

class LegalEntityDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = LegalEntity

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['member'] = self.request.user.member_of(context['object'].pk)
        return context


class LegalEntityList(AutoPermissionRequiredMixin, generic.ListView):
    permission_type = 'view'
    model = LegalEntity

class LegalEntityMemberList(AutoPermissionRequiredMixin, generic.DetailView):
    permission_type = 'change'
    template_name = 'projects/legalentity_member_list.html'
    model = LegalEntity

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['form'] = UserAutocompleteForm()
        return context

@permission_required('projects.change_legal_entity', fn=objectgetter(LegalEntity, 'legal_entity_id'))
def legal_member_add(request, legal_entity_id):
    user_id = request.POST.get('user')
    user = get_object_or_404(User, pk=user_id)
    legal_entity = get_object_or_404(LegalEntity, pk=legal_entity_id)
    user.legal_entities.add(legal_entity)
    messages.success(request, _("Success"))

    return redirect('projects:legal_member_list', legal_entity_id)

@permission_required('projects.change_legal_entity', fn=objectgetter(LegalEntity, 'legal_entity_id'))
def legal_member_remove(request, legal_entity_id, user_id):
    user = get_object_or_404(User, pk=user_id)
    legal_entity = get_object_or_404(LegalEntity, pk=legal_entity_id)
    user.legal_entities.remove(legal_entity)
    messages.success(request, _("Success"))

    return redirect('projects:legal_member_list', legal_entity_id)

class ReportForm(AutoPermissionRequiredMixin, ModelForm):
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

class ReportCreate(AutoPermissionRequiredMixin, CreateView):
    model = Report
    form_class = ReportForm

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        context['project'] = self.project
        return context

    def form_valid(self, form):
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        form.instance.project = self.project
        return super().form_valid(form)

class ReportUpdate(AutoPermissionRequiredMixin, UpdateView):
    model = Report
    form_class = ReportForm

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

class ReportDelete(AutoPermissionRequiredMixin, DeleteView):
    model = Report
    template_name = 'projects/project_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})

class ReportDetails(AutoPermissionRequiredMixin, generic.DetailView):
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

class ReportList(AutoPermissionRequiredMixin, generic.ListView):
    model = Report
    permission_type = 'view'

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

class MoneySupportForm(AutoPermissionRequiredMixin, ModelForm):
    class Meta:
        model = MoneySupport
        fields=['leva', 'comment' ]
        widgets = {
        }

    def __init__(self, *args, **kwargs):
        necessity = kwargs.pop('necessity')
        super().__init__(*args, **kwargs)
        self.fields['leva'].initial = necessity.price

class MoneySupportCreate(AutoPermissionRequiredMixin, CreateView):
    model = MoneySupport
    form_class = MoneySupportForm
    template_name = 'projects/support_form.html'

    def get_form_kwargs(self):
        necessity_id = self.kwargs['necessity']
        necessity = get_object_or_404(ThingNecessity, pk=necessity_id)
        kwargs = super().get_form_kwargs()
        kwargs.update({'necessity': necessity})
        return kwargs

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        context['project'] = self.project

        necessity_id = self.kwargs['necessity']
        necessity = get_object_or_404(ThingNecessity, pk=necessity_id)
        context['necessity'] = necessity

        return context

    def form_valid(self, form):
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        form.instance.project = self.project

        user = self.request.user
        form.instance.user = user

        necessity_id = self.kwargs['necessity']
        necessity = get_object_or_404(ThingNecessity, pk=necessity_id)

        form.instance.necessity = necessity

        return super().form_valid(form)

#TODO only allow if support is not accepted
class MoneySupportUpdate(AutoPermissionRequiredMixin, UpdateView):
    model = MoneySupport
    form_class = MoneySupportForm
    template_name = 'projects/support_form.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

class MoneySupportDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = MoneySupport
    template_name = 'projects/support_detail.html'

#TODO only allow if support is not accepted
class SupportDelete(AutoPermissionRequiredMixin, DeleteView):
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

def get_support(pk, type):
    if type in ['money', 'm']:
        support = get_object_or_404(MoneySupport, pk=pk)
    else:
        support = get_object_or_404(TimeSupport, pk=pk)

    return support

def get_support_request(request, pk, type, *args, **kwargs):
    return get_support(pk, type)

def support_accept(request, pk, type):
    return support_change_accept(request, pk, type, True)

def support_decline(request, pk, type):
    return support_change_accept(request, pk, type, False)

@permission_required('projects.accept_support', fn=get_support_request)
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

@permission_required('projects.mark_delivered_support', fn=get_support_request)
def support_delivered(request, pk, type):
    if type in ['money', 'm']:
        support = get_object_or_404(MoneySupport, pk=pk)
    else:
        support = get_object_or_404(TimeSupport, pk=pk)

    support = get_support(pk, type)

    if support.delivered:
        messages.info(request, _('Support already marked as delivered'))
    else:
        support.delivered = True
        support.delivered_at = timezone.now()
        support.save()

        messages.success(request, _('Support marked as delivered'))

    return redirect(support)

@permission_required('projects.list_support', fn=objectgetter(Project, 'project_id'))
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

@permission_required('projects.add_support', fn=objectgetter(Project, 'project_id'))
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

class TimeSupportForm(AutoPermissionRequiredMixin, ModelForm):
    class Meta:
        model = TimeSupport
        fields=['comment']

    def __init__(self, *args, **kwargs):
        necessities = kwargs.pop('necessity_ids')
        super().__init__(*args, **kwargs)
        self.fields['price'].initial = necessity.price
        self.fields['start_date'].initial = necessity.start_date
        self.fields['end_date'].initial = necessity.end_date

class TimeSupportCreate(AutoPermissionRequiredMixin, CreateView):
    model = TimeSupport
    form_class = TimeSupportForm
    template_name = 'projects/support_form.html'

    def get_form_kwargs(self):
        necessity_ids = self.kwargs['necessities'].split(',')
        kwargs = super().get_form_kwargs()
        kwargs.update({'necessity_ids': necessity_ids})
        return kwargs

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        context['project'] = self.project

        necessity_ids = self.kwargs['necessities'].split(',')
        necessity_list = map(lambda n: get_object_or_404(TimeNecessity, pk=n), necessity_ids)
        context['necessity_list'] = necessity

        return context

    def form_valid(self, form):
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        form.instance.project = self.project

        user = self.request.user
        form.instance.user = user

        necessity_id = self.kwargs['necessity']
        necessity = get_object_or_404(TimeNecessity, pk=necessity_id)

        form.instance.necessity = necessity

        return super().form_valid(form)

#TODO only allow if support is not accepted
class TimeSupportUpdate(AutoPermissionRequiredMixin, UpdateView):
    model = TimeSupport
    form_class = TimeSupportForm
    template_name = 'projects/support_form.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

class TimeSupportDetails(AutoPermissionRequiredMixin, generic.DetailView):
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

class UserAutocompleteForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label=_("Email:"),
        widget=autocomplete.ModelSelect2(
            url='projects:user_autocomplete',
            attrs={
                'data-html': True,
            }
        )
    )

#TODO authenticate with rules
class UserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return User.objects.none()

        if self.q and '@' in self.q:
            qs = User.objects.all()
            qs = qs.filter(email=self.q)
        else:
            qs = User.objects.none()

        return qs

    def get_result_label(self, item):
        return format_html('%s %s' % (item.first_name, item.last_name))

@permission_required('projects.accept_support', fn=objectgetter(Project, 'pk'))

def follow_project(request, pk):

    project = get_object_or_404(Project, pk=pk)

    user = request.user

    news_feeds = feed_manager.get_news_feeds(user.id)
    notification_feed = feed_manager.get_notification_feed(user.id)

    for feed in news_feeds.values():
        feed.follow('project', project.id)

    notification_feed.follow('project', project.id)
    messages.success(request, "%s %s" % (_("Started following"),project))

    return redirect(project)

class AnnouncementCreate(AutoPermissionRequiredMixin, CreateView):
    model = Announcement
    fields = ['text']

    def form_valid(self, form):
        project_pk = self.kwargs['project']
        self.project = get_object_or_404(Project, pk=project_pk)
        form.instance.project = self.project 
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})

class AnnouncementUpdate(AutoPermissionRequiredMixin, UpdateView):
    model = Announcement
    fields = ['text']

    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})

class AnnouncementDelete(AutoPermissionRequiredMixin, DeleteView):
    model = Announcement

    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})

class AnnouncementDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = Announcement

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        return context

def time_support_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    
    context = {}
    context['project'] = project
    necessity_list = project.timenecessity_set.all()
    context['necessity_list'] = necessity_list

    TimeSupportFormset = modelformset_factory(
        TimeSupport,
        fields=['necessity', 'comment', 'start_date', 'end_date', 'price' ],
        widgets={
            'start_date': forms.HiddenInput(),
            'end_date': forms.HiddenInput(),
            'price': forms.HiddenInput(),
            'comment': forms.Textarea({
                'rows': 1,
                'cols': 30
                }
        )},
        extra=len(necessity_list))

    initial = list(map(lambda n: {'necessity': n, 'start_date': n.start_date, 'end_date': n.end_date, 'price': n.price}, necessity_list))
    if request.method == 'GET':
        formset = TimeSupportFormset(
            queryset=TimeSupport.objects.none(),
            initial=initial)

    elif request.method == 'POST':
        formset = TimeSupportFormset(
            request.POST,
            queryset=TimeSupport.objects.none(),
            initial=initial)

        selected_necessities = request.POST.getlist('necessity')
        selected_necessities = list(map(int, selected_necessities))

        if not selected_necessities:
            messages.error(request, _("Choose at least one necessity"))

        else:
            if formset.is_valid():
                saved = 0
                for form in formset:
                    necessity = form.cleaned_data.get('necessity')
                    if necessity and necessity.pk in selected_necessities:
                        form.instance.project = project
                        form.instance.user = request.user
                        form.save()
                        saved += 1
                if saved > 0:
                    messages.success(request, _('Submitted %d support candidates' % saved))
                    return redirect(project)

    context['formset'] = formset

    return render(request, 'projects/time_support_create.html', context)

class TimeNecessityList(AutoPermissionRequiredMixin, generic.ListView):
    permission_type = 'view'
    model = TimeNecessity

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project_pk = self.kwargs['project_id']
        project = get_object_or_404(Project, pk=project_pk)
        context['project'] = project

        context['necessity_list'] = project.timenecessity_set.all()
        context['type'] = 'time'

        context['member'] = self.request.user.member_of(project.legal_entity.pk)

        return context

class ThingNecessityList(AutoPermissionRequiredMixin, generic.ListView):
    permission_type = 'view'
    model = ThingNecessity

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project_pk = self.kwargs['project_id']
        project = get_object_or_404(Project, pk=project_pk)
        context['project'] = project

        context['necessity_list'] = project.thingnecessity_set.all()
        context['type'] = 'thing'

        context['member'] = self.request.user.member_of(project.legal_entity.pk)

        return context

class TimeNecessityDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = TimeNecessity

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['type'] = 'time'
        return context

class ThingNecessityDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = ThingNecessity

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['type'] = 'thing'
        return context




