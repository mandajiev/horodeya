import os
import uuid

from requests.exceptions import Timeout, ConnectionError

from django.utils import timezone

from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.utils.text import slugify
from django.utils.html import format_html
from django.forms import ModelForm, ValidationError, inlineformset_factory, modelformset_factory

from django import forms
from django.db.models import Q

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from django.utils.translation import gettext as _

from rules.contrib.views import AutoPermissionRequiredMixin, permission_required, objectgetter, PermissionRequiredMixin

from projects.models import Project, Community, Report, MoneySupport, TimeSupport, User, Announcement, TimeNecessity, ThingNecessity, Question, QuestionPrototype, DonatorData, LegalEntityDonatorData

from projects.forms import QuestionForm, PaymentForm

from tempus_dominus.widgets import DateTimePicker, DatePicker

from vote.models import UP, DOWN

from photologue.models import Photo, Gallery

from dal import autocomplete

from stream_django.feed_manager import feed_manager
from stream_django.enrich import Enrich
from django.contrib.auth.mixins import UserPassesTestMixin


def short_random():
    return str(uuid.uuid4()).split('-')[0]


COMMUNITY_ACTIVYTY_TYPES = [('Creativity', 'Наука и творчество'),
                            ('Education', 'Просвета и възпитание'),
                            ('Art', 'Култура и артистичност'),
                            ('Administration', 'Администрация и финанси'),
                            ('Willpower', 'Спорт и туризъм'),
                            ('Health', 'Бит и здравеопазване'),
                            ('Food', 'Земеделие и изхранване')]


class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'community', 'category', 'location', 'description', 'goal',
                  'text', 'start_date', 'end_date', 'end_date_tasks', 'report_period']
        widgets = {
            'end_date': DatePicker(
                options={
                    'useCurrent': True,
                    'collapse': False,
                }
            ),
            'start_date': DatePicker(
                options={
                    'useCurrent': True,
                    'collapse': False,
                }
            ),
            'end_date_tasks': DatePicker(
                options={
                    'useCurrent': True,
                    'collapse': False,
                }
            ),
            'category': forms.RadioSelect(attrs=None, choices=COMMUNITY_ACTIVYTY_TYPES)
        }
        labels = {
            'goal1': 'Goal 1 ',
            'goal2': 'Goal 2',
            'goal3': 'Goal 3',
            'text': 'Text(5000 characters)'
        }

    def clean_end_date(self):
        startDate = self.cleaned_data['start_date']
        endDate = self.cleaned_data['end_date']
        if endDate <= startDate:
            raise forms.ValidationError(_(
                'End date must be after  start date'), code='invalid')

        return endDate

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['community'].queryset = user.communities


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
    fields=['name', 'description', 'count', 'price', 'start_date', 'end_date'],
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
    fields=['name', 'description', 'count', 'price'],
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


@login_required
@permission_required('projects.change_thingnecessity', fn=objectgetter(Project, 'project_id'))
def thing_necessity_update(request, project_id):
    return necessity_update(request, project_id, 'thing')


@login_required
@permission_required('projects.change_timenecessity', fn=objectgetter(Project, 'project_id'))
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

                formset = cls(instance=project)  # за да добави празен ред
            else:
                if type == 'time':
                    return redirect('projects:time_necessity_list', project.pk)
                else:
                    return redirect('projects:thing_necessity_list', project.pk)

    return render(request, 'projects/necessity_form.html', {
        'formset': formset,
        'project': project,
        'type': type
    })


class ProjectDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = Project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        show_admin = self.request.GET.get('show_admin', 'True') == 'True'
        can_be_admin = self.request.user.is_authenticated and self.request.user.member_of(
            context['object'].community_id)
        context['admin'] = show_admin and can_be_admin
        context['can_be_admin'] = can_be_admin

        try:
            feed = feed_manager.get_feed('project', context['object'].id)
            enricher = Enrich()
            timeline = enricher.enrich_activities(
                feed.get(limit=25)['results'])
            context['timeline'] = timeline
        except (Timeout, ConnectionError):
            messages.error(_('Could not get timeline'))
            context['timeline'] = None

        context['announcement_form'] = AnnouncementForm()

        return context


class ProjectCreate(AutoPermissionRequiredMixin, UserPassesTestMixin, CreateView):
    model = Project
    form_class = ProjectForm

    def handle_no_permission(self):
        return redirect('/projects/community/create')

    def test_func(self):
        return self.request.user.communities.count() > 0

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
        community = project.community
        if community.admin != user:
            form.add_error('community', 'You must be the admin of the community entity. Admin for %s is %s' % (
                community, community.admin))
            return super().form_invalid(form)

        project.type = self.kwargs['type']

        # Потребител 0 следва всички проекти
        user_follow_project(0, project)

        return super().form_valid(form)


# class ProjectUpdate(AutoPermissionRequiredMixin, UpdateView):
#     model = Project
#     form_class = ProjectForm

#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs.update({'user': self.request.user})
#         return kwargs

#     def form_valid(self, form):
#         user = self.request.user
#         community = form.instance.community
#         if community.admin != user:
#             form.add_error('community', 'You must be the admin of the community entity. Admin for %s is %s' % (
#                 community, community.admin))
#             return super().form_invalid(form)
#         return super().form_valid(form)


class ProjectDelete(AutoPermissionRequiredMixin, DeleteView):
    model = Project
    success_url = '/'


COMMUNITY_FIELDS = ['name', 'type', 'bulstat', 'DDORegistration', 'phone', 'email', 'mission',
                    'numberOfSupporters', 'previousExperience', 'activityType', 'website', 'facebook_page']


class CommunityCreate(AutoPermissionRequiredMixin, CreateView):
    model = Community
    fields = COMMUNITY_FIELDS

    def get_form(self, form_class=None):
        form = super(CommunityCreate, self).get_form(form_class)
        form.fields['activityType'].widget = forms.RadioSelect(
            attrs=None, choices=COMMUNITY_ACTIVYTY_TYPES)
        form.fields['type'].widget.attrs['readonly'] = True
        return form

    def form_valid(self, form):
        user = self.request.user
        form.instance.admin = user
        community = form.save(commit=False)
        community.save()
        user.communities.add(community)
        return super().form_valid(form)


class CommunityUpdate(AutoPermissionRequiredMixin, UpdateView):
    model = Community
    fields = COMMUNITY_FIELDS

    def form_valid(self, form):
        admin = form.instance.admin
        if not admin.communities.filter(pk=form.instance.pk).exists():
            admin.communities.add(form.instance)

        return super().form_valid(form)


class CommunityDelete(AutoPermissionRequiredMixin, DeleteView):
    model = Community
    success_url = reverse_lazy('projects:community_list')


class CommunityDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = Community

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['member'] = self.request.user.member_of(context['object'].pk)
        return context


class CommunityList(AutoPermissionRequiredMixin, generic.ListView):
    permission_type = 'view'
    model = Community


class CommunityMemberList(AutoPermissionRequiredMixin, generic.DetailView):
    permission_type = 'change'
    template_name = 'projects/community_member_list.html'
    model = Community

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['form'] = UserAutocompleteForm()
        return context


@permission_required('projects.change_community', fn=objectgetter(Community, 'community_id'))
def community_member_add(request, community_id):
    user_id = request.POST.get('user')
    user = get_object_or_404(User, pk=user_id)
    community = get_object_or_404(Community, pk=community_id)
    user.communities.add(community)
    messages.success(request, _("Success"))

    return redirect('projects:community_member_list', community_id)


@permission_required('projects.change_community', fn=objectgetter(Community, 'community_id'))
def community_member_remove(request, community_id, user_id):
    user = get_object_or_404(User, pk=user_id)
    community = get_object_or_404(Community, pk=community_id)
    user.communities.remove(community)
    messages.success(request, _("Success"))

    return redirect('projects:community_member_list', community_id)


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


class ReportCreate(PermissionRequiredMixin, CreateView):
    model = Report
    form_class = ReportForm

    def get_permission_object(self):
        project_pk = self.kwargs['project']
        return get_object_or_404(Project, pk=project_pk)

    permission_required = ('projects.add_report')

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

        context['reports'] = Report.objects.filter(
            project_id=project_pk, published_at__lte=now)
        context['unpublished_reports'] = Report.objects.filter(
            project_id=project_pk, published_at__gt=now)

        return context


def report_vote_up(request, pk):
    return report_vote(request, pk, UP)


def report_vote_down(request, pk):
    return report_vote(request, pk, DOWN)


@login_required
# TODO must be a subscriber to vote
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
            messages.success(request, _('Voted up')
                             if action == UP else _('Voted down'))

    return redirect(report)


class MoneySupportForm(ModelForm):
    class Meta:
        model = MoneySupport
        fields = ['leva', 'necessity', 'comment',
                  'payment_method']
        widgets = {
            'payment_method': forms.RadioSelect()
        }

    def __init__(self, *args, **kwargs):
        if 'project' in kwargs:
            project = kwargs.pop('project')
        else:
            project = None

        super().__init__(*args, **kwargs)

        if not project:
            project = kwargs.get('instance').project

        self.fields['necessity'].queryset = project.thingnecessity_set
        self.fields['necessity'].empty_label = _('Any will do')


class MoneySupportCreate(AutoPermissionRequiredMixin, CreateView):
    model = MoneySupport
    template_name = 'projects/support_form.html'
    form_class = MoneySupportForm

    def get_form_kwargs(self):
        project_pk = self.kwargs['project']
        project = get_object_or_404(Project, pk=project_pk)
        kwargs = super().get_form_kwargs()
        kwargs.update({'project': project})
        return kwargs

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

        user = self.request.user
        form.instance.user = user

        return super().form_valid(form)

# TODO only allow if support is not accepted


class MoneySupportUpdate(AutoPermissionRequiredMixin, UpdateView):
    model = MoneySupport
    template_name = 'projects/support_form.html'
    form_class = MoneySupportForm

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['project'] = self.object.project

        return context


@login_required
def money_support_create(request, project_id=None):
    supporterType = request.GET.get('supportertype')
    if(supporterType == 'donator'):
        if(request.user.donatorData):
            return money_support_crud(request, project_id=project_id)
        else:
            return redirect('/projects/donator/create/?next=/projects/%s/moneysupport/create/' % (project_id))
    elif (supporterType == 'legalentitydonator'):
        if(request.user.legalEntityDonatorData):
            return money_support_crud(request, project_id=project_id)
        else:
            return redirect('/projects/legalentitydonator/create/?next=/projects/%s/moneysupport/create/' % (project_id))


@permission_required('projects.update_moneysupport', fn=objectgetter(MoneySupport, 'support_id'))
def money_support_update(request, project_id=None, support_id=None):
    return money_support_crud(request, support_id=support_id)


def money_support_crud(request, project_id=None, support_id=None):
    Form = MoneySupportForm
    template = 'projects/support_form.html'
    supportType = request.GET.get('supportertype')
    if project_id:
        project = get_object_or_404(Project, pk=project_id)
        support = None
    else:
        support = get_object_or_404(MoneySupport, pk=support_id)
        project = support.project

    payment_form = None
    action_text = _('Next step')
    if request.method == 'GET':
        form = Form(instance=support, project=project, prefix='step_1')

    elif request.method == 'POST':
        form = Form(request.POST, instance=support,
                    project=project, prefix='step_1')
        if form.is_valid():
            if 'go_back' in request.POST:
                payment_form = None
            elif 'step_2-accept' in request.POST:
                # We only validate data if this is a step_2 submit, if only a step_1 submit  validation on step_2 printed on the form may confuse the user
                payment_form = PaymentForm(
                    request.POST, payment_method=form.cleaned_data['payment_method'], payment_amount=form.cleaned_data['leva'], community=project.community, prefix='step_2')
            else:
                payment_form = PaymentForm(
                    payment_method=form.cleaned_data['payment_method'], payment_amount=form.cleaned_data['leva'], community=project.community, prefix='step_2')

            if payment_form:
                action_text = payment_form.action_text
                if payment_form.is_valid():
                    form.instance.project = project
                    form.instance.user = request.user
                    support = form.save(commit=False)
                    support.supportType = supportType
                    support.save()
                    return redirect(form.instance)

    return render(request, template, {
        'form': form,
        'project': project,
        'action_text': action_text,
        'payment_form': payment_form
    })


class MoneySupportDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = MoneySupport
    template_name = 'projects/support_detail.html'

# TODO only allow if support is not accepted


class MoneySupportDelete(AutoPermissionRequiredMixin, DeleteView):
    model = MoneySupport
    template_name = 'projects/project_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('projects:details', kwargs={'pk': self.object.project.pk})


class TimeSupportDelete(AutoPermissionRequiredMixin, DeleteView):
    model = TimeSupport
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
            messages.success(request, _('Voted up')
                             if action == UP else _('Voted down'))

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

    if support.STATUS == support.STATUS.accepted:
        messages.info(request, _('Support already accepted')
                      if accepted else _('Support already declined'))
    else:
        if type in ['money', 'm'] and not support.necessity:
            messages.info(request, _(
                'Select a necessity for the money support'))
            return redirect('projects:money_support_update', support.pk)

        result = support.set_accepted(accepted)
        if result == accepted:
            messages.success(request, _('Support accepted')
                             if accepted else _('Support declined'))
        else:
            messages.error(request, _('Support could not be accepted')
                           if accepted else _('Support could not be declined'))

    return redirect(support)


@permission_required('projects.mark_delivered_support', fn=get_support_request)
def support_delivered(request, pk, type):
    if type in ['money', 'm']:
        support = get_object_or_404(MoneySupport, pk=pk)
    else:
        support = get_object_or_404(TimeSupport, pk=pk)

    support = get_support(pk, type)

    if support.STATUS == support.STATUS.delivered:
        messages.info(request, _('Support already marked as delivered'))
    else:
        support.STATUS = support.STATUS.delivered
        # support.delivered_at = timezone.now()
        support.save()

        messages.success(request, _('Support marked as delivered'))

    return redirect(support)


class TimeSupportForm(AutoPermissionRequiredMixin, ModelForm):
    class Meta:
        model = TimeSupport
        fields = ['comment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@permission_required('projects.change_timesupport', fn=objectgetter(TimeSupport, 'pk'))
def time_support_update(request, pk):
    time_support = get_object_or_404(TimeSupport, pk=pk)
    return time_support_create_update(request, time_support.project, time_support)


class TimeSupportDetails(AutoPermissionRequiredMixin, generic.DetailView):
    model = TimeSupport
    template_name = 'projects/support_detail.html'


def user_support_list(request, user_id, type):
    user = get_object_or_404(User, pk=user_id)
    if type == 'time':
        support_list = user.timesupport_set.order_by('-status_since')

    else:
        support_list = user.moneysupport_set.order_by('-status_since')

    return render(request, 'projects/user_support_list.html', context={
        'account': user,
        'type': type,
        'support_list': support_list,
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
    # TODO use stream framework for this
    # for m in money_supported:
    #    supported_projects.add(m.project)

    # for t in time_supported:
    #    supported_projects.add(t.project)

    # for p in supported_projects:
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

# TODO authenticate with rules


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


@permission_required('projects.follow_project', fn=objectgetter(Project, 'pk'))
def follow_project(request, pk):

    project = get_object_or_404(Project, pk=pk)

    user = request.user

    user_follow_project(user.id, project)

    messages.success(request, "%s %s" % (_("Started following"), project))

    return redirect(project)


def user_follow_project(user_id, project):
    news_feeds = feed_manager.get_news_feeds(user_id)

    for feed in news_feeds.values():
        feed.follow('project', project.id)

    notification_feed = feed_manager.get_notification_feed(user_id)
    notification_feed.follow('project', project.id)


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


@permission_required('projects.add_timesupport', fn=objectgetter(Project, 'project_id'))
def time_support_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return time_support_create_update(request, project)


def time_support_create_update(request, project, support=None):
    context = {}
    context['project'] = project
    queryset = TimeSupport.objects.filter(project=project, user=request.user)
    applied_necessities = set(map(lambda ts: ts.necessity, queryset.all()))
    answers = project.answer_set.all()

    necessity_list = project.timenecessity_set.all()
    necessity_list = list(
        filter(lambda n: n not in applied_necessities, necessity_list))

    TimeSupportFormset = modelformset_factory(
        TimeSupport,
        fields=['necessity', 'comment', 'start_date', 'end_date', 'price'],
        labels={'comment': _(
            'Why do you apply for this position? List your relevant experience / skills')},
        widgets={
            'start_date': forms.HiddenInput(),
            'end_date': forms.HiddenInput(),
            'price': forms.HiddenInput(),
            'comment': forms.Textarea(
                attrs={
                    'rows': 1,
                    'cols': 30,
                },
            )},
        extra=len(necessity_list))

    initial = list(map(lambda n: {'necessity': n, 'start_date': n.start_date,
                                  'end_date': n.end_date, 'price': n.price}, necessity_list))
    questions = project.question_set.order_by('order').all()
    if request.method == 'GET':
        formset = TimeSupportFormset(
            queryset=queryset,
            initial=initial)
        question_form = QuestionForm(questions=questions, answers=answers)

    elif request.method == 'POST':
        formset = TimeSupportFormset(
            request.POST,
            queryset=queryset,
            initial=None)

        question_form = QuestionForm(request.POST, questions=questions)

        selected_necessities = request.POST.getlist('necessity')
        selected_necessities = list(map(int, selected_necessities))

        if not selected_necessities:
            messages.error(request, _(
                "Choose at least one volunteer position"))

        else:
            if question_form.is_valid():
                question_form.save(project)
            if formset.is_valid():
                saved = 0
                for form in formset:
                    necessity = form.cleaned_data.get('necessity')
                    if necessity and necessity.pk in selected_necessities:
                        form.instance.project = project
                        form.instance.user = request.user
                        form.save()
                        saved += 1

                messages.success(request, _(
                    'Applied to %d volunteer positions' % saved))
                return redirect(project)

    context['formset'] = formset
    context['form'] = question_form
    context['update'] = support is not None

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

        context['member'] = self.request.user.member_of(project.community.pk)

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

        context['member'] = self.request.user.member_of(project.community.pk)

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


class UploadFileForm(forms.Form):
    file = forms.FileField(required=False)
    delete = forms.BooleanField(initial=False, required=False)


PhotoFormset = modelformset_factory(
    Photo,
    fields=['image'],
    extra=1,
    can_delete=True,
    can_order=True)


def neat_photo(first_directory, second_directory, image):
    path, extension = os.path.splitext(image.name)
    image.name = short_random() + extension

    photo = Photo()
    photo.title = image.name
    photo.image = image
    photo.slug = slugify(image.name)

    # Нашият PHOTOLOGUE_PATH използва това за да реши къде да запише файла
    photo.first_directory = first_directory
    photo.second_directory = second_directory

    photo.save()

    return photo


def gallery_update(request, project_id):
    template_name = 'projects/photo_form.html'
    project = get_object_or_404(Project, pk=project_id)

    # TODO make project.name unique
    gallery, created = Gallery.objects.get_or_create(
        title=project.name,
        defaults={
            'slug': slugify(project.name, allow_unicode=True)
        })

    if created:
        project.gallery = gallery
        project.save()

    if request.method == 'GET':
        # we don't want to display the already saved model instances
        formset = PhotoFormset(queryset=gallery.photos.all())

    elif request.method == 'POST':
        formset = PhotoFormset(request.POST, queryset=gallery.photos.all())
        if formset.is_valid():
            for form in formset:
                image = request.FILES.get("%s-image" % (form.prefix))
                order = form.cleaned_data.get('ORDER', len(formset))
                if form.instance.id and form.cleaned_data.get('DELETE'):
                    form.instance.delete()
                elif image:
                    photo = neat_photo('project', str(project_id), image)
                    photo.galleries.add(gallery)

                    through = gallery.photos.through.objects.get(
                        photo_id=photo.pk, gallery_id=gallery.pk)
                    through.sort_value = order
                    through.save()
                elif form.instance.image:
                    image = form.instance
                    through = gallery.photos.through.objects.get(
                        photo_id=image.pk, gallery_id=gallery.pk)
                    through.sort_value = order
                    through.save()

            return redirect(project)

    return render(request, 'projects/photo_form.html', {
        'formset': formset,
        'project': project,
    })


@permission_required('projects.change_user', fn=objectgetter(User, 'user_id'))
def user_photo_update(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():

            title = str(user)
            slug = slugify(title, allow_unicode=True)

            if user.photo:
                user.photo.delete()

            if form.cleaned_data.get('delete'):
                messages.success(request, _('Image deleted'))
            else:
                user.photo = neat_photo('user', str(
                    user_id), request.FILES['file'])
                user.save()

                messages.success(request, _('Image uploaded'))
            next = request.GET.get('next')
            if next:
                return redirect(request.GET['next'])
            else:
                return redirect(user)
    else:
        form = UploadFileForm(
            initial={'file': user.photo.image if user.photo else None})

    return render(request, 'projects/user_photo_update.html', {'form': form, 'user': user})


@permission_required('projects.change_community', fn=objectgetter(Community, 'pk'))
def community_photo_update(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            title = str(community)
            slug = slugify(title, allow_unicode=True)

            if community.photo:
                community.photo.delete()

            if form.cleaned_data.get('delete'):
                messages.success(request, _('Image deleted'))
            else:
                community.photo = neat_photo(
                    'community', str(pk), request.FILES['file'])
                community.save()

                messages.success(request, _('Image uploaded'))

            next = request.GET.get('next')
            if next:
                return redirect(request.GET['next'])
            else:
                return redirect(community)
    else:
        # form = UploadFileForm(
        #     initial={'file': community.photo.image if community.photo else None})
        form = UploadFileForm()

    return render(request, 'projects/community_photo_update.html', {'form': form, 'community': community})


@permission_required('projects.change_question', fn=objectgetter(Project, 'project_id'))
def questions_update(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if project.question_set.count() == 0:
        prototypes = QuestionPrototype.objects.order_by('order').all()
    else:
        prototypes = []

    initial = list(map(lambda p: {
                   'prototype': p[1], 'required': p[1].required, 'ORDER': p[0]+1}, enumerate(prototypes)))

    QuestionFormset = modelformset_factory(
        Question,
        fields=['prototype', 'description', 'required'],
        widgets={
            'description': forms.Textarea({
                'rows': 1,
                'cols': 30
            }
            ),
        },
        can_order=True,
        can_delete=True,
        extra=len(prototypes))

    cls = QuestionFormset
    template_name = 'projects/questions_form.html'

    if request.method == 'GET':
        formset = cls(initial=initial, queryset=Question.objects.filter(
            project=project).order_by('order'))

    elif request.method == 'POST':
        formset = cls(request.POST)
        if formset.is_valid():
            for form in formset:
                order = form.cleaned_data.get('ORDER', len(formset))
                if form.cleaned_data.get('DELETE'):
                    form.instance.delete()

                elif form.cleaned_data.get('prototype'):
                    form.instance.project = project
                    if order:
                        form.instance.order = order
                    form.save()

            return redirect('projects:time_necessity_list', project.pk)

    return render(request, template_name, {
        'formset': formset,
        'project': project
    })


class DonatorDataCreate(AutoPermissionRequiredMixin, CreateView):
    model = DonatorData
    fields = ['phone', 'citizenship', 'domicile', 'postAddress',
              'TIN', 'passportData', 'birthdate', 'placeOfBirth',
              'profession', 'website']
    redirectUrl = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        redirectUrl = self.request.GET.get('next')
        return context

    def get_form(self, form_class=None):
        form = super(DonatorDataCreate, self).get_form(form_class)
        form.fields['birthdate'].widget = DatePicker(
            attrs={
                'style': 'width:120px'
            },
            options={
                'useCurrent': True,
                'collapse': False,
            },
        )
        return form

    def form_valid(self, form):
        user = self.request.user
        data = form.save(commit=False)
        data.save()
        user.donatorData = data
        user.save()
        redirectUrl = self.request.GET.get('next')
        if(redirectUrl):
            return redirect(self.request.GET['next']+'?supportertype=donator')
        else:
            return redirect('/accounts/profile/')


class LegalEntityDataCreate(AutoPermissionRequiredMixin, CreateView):
    model = LegalEntityDonatorData
    fields = ['name', 'type', 'EIK',
              'DDORegistration', 'phoneNumber', 'website']

    def form_valid(self, form):
        user = self.request.user
        data = form.save(commit=False)
        data.save()
        user.legalEntityDonatorData = data
        user.save()
        redirectUrl = self.request.GET.get('next')
        if(redirectUrl):
            return redirect(self.request.GET['next']+'?supportertype=legalentitydonator')
        else:
            return redirect('/accounts/profile/')
