from django.utils import timezone
import datetime

from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import get_language

from django.core.validators import MaxValueValidator

from django.contrib.auth.models import AbstractUser

from model_utils import Choices

import rules
from rules.contrib.models import RulesModelBase, RulesModelMixin

from vote.models import VoteModel, UP, DOWN

from stream_django.activity import Activity

from requests.exceptions import ConnectionError

from django.utils.translation import gettext, gettext_lazy as _

from photologue.models import Photo, Gallery

def determine_community(object):
    if isinstance(object, Project):
        return object.community
    elif isinstance(object, Report) or isinstance(object, Support):
        return object.project.community

    return object

@rules.predicate
def member_of_community(user, object):
    return user.member_of(determine_community(object).id)

@rules.predicate
def admin_of_community(user, object):
    return user == determine_community(object).admin

@rules.predicate
def myself(user, user2):
    if isinstance(user2, User):
        return user == user2

    return user == user2.user

@rules.predicate
def has_a_community(user):
    return user.communities.count() > 0

@rules.predicate
def is_accepted(user, support):
    return support.status == support.STATUS.accepted

class Timestamped(RulesModelMixin, models.Model, metaclass=RulesModelBase):
    created_at = models.DateTimeField(editable=False)
    updated_at = models.DateTimeField(editable=False)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()

        self.updated_at = timezone.now()
        return super(Timestamped, self).save(*args, **kwargs)

    class Meta:
        abstract = True

class Community(Timestamped):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": admin_of_community,
            "change": admin_of_community,
            "view": rules.is_authenticated,
            "leave": member_of_community & ~admin_of_community
        }

    name = models.CharField(max_length=100)
    text = models.TextField()
    bulstat = models.DecimalField(blank=True, null=True, max_digits=20, decimal_places=0)
    email = models.EmailField()
    phone = models.DecimalField(blank=True, null=True, max_digits=20, decimal_places=0)
    admin = models.ForeignKey('User', on_delete=models.PROTECT)
    bank_account_iban = models.CharField(blank=True, null=True, max_length=34)
    bank_account_bank_code = models.CharField(blank=True, null=True, max_length=34)
    bank_account_name = models.CharField(blank=True, null=True, max_length=100)
    revolut_phone = models.DecimalField(blank=True, null=True, max_digits=20, decimal_places=0)
    bal = models.IntegerField(default=20, validators=[MaxValueValidator(100)])
    photo = models.ForeignKey(Photo, on_delete=models.SET_NULL, blank=True, null=True)

    def page_name(self):
        return "%s %s" % (gettext('Community'), self.name)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:community_details', kwargs={'pk': self.pk})

class User(AbstractUser, RulesModelMixin, metaclass=RulesModelBase):
    class Meta:
        rules_permissions = {
            "add": rules.always_allow,
            "delete": rules.always_deny,
            "change": myself,
            "view": rules.is_authenticated,
        }

    communities = models.ManyToManyField(Community)
    bal = models.IntegerField(default=20, validators=[MaxValueValidator(100)])
    photo = models.ForeignKey(Photo, on_delete=models.SET_NULL, null=True)

    def page_name(self):
        return "%s %s" % (gettext('User'), str(self))

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

    def get_absolute_url(self):
        return reverse('account', kwargs={'pk': self.pk})

    def member_of(self, community_pk):
        return self.communities.filter(pk=community_pk).exists()

    def total_support_count(self):
        return self.moneysupport_set.count() + self.timesupport_set.count()

    def total_votes_count(self):
        return len(Report.votes.all(self.pk, UP)) + len(Report.votes.all(self.pk, DOWN))

#TODO notify user on new project added
class Project(Timestamped):
    class Meta:
        rules_permissions = {
            "add": admin_of_community,
            "delete": admin_of_community,
            "change": member_of_community,
            "view": rules.always_allow,
            "follow": rules.is_authenticated
        }

    TYPES = Choices('business', 'cause')
    type = models.CharField(max_length=20, choices=TYPES)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=300)
    text = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    end_date = models.DateField(null=True, blank=True)
    gallery = models.ForeignKey(Gallery, on_delete=models.PROTECT, null=True)

    def latest_reports(self):
        show_reports = 3
        ordered = self.report_set.order_by('-published_at')
        return ordered[:show_reports], ordered.count() - show_reports

    def page_name(self):
        return "%s %s" % (gettext('Cause') if self.type == 'cause' else gettext('Business'), self.name)

    def key(self):
        return 'project-%d' % self.id

    def __str__(self):
        return ' - '.join([self.community.name, self.name])

    def get_absolute_url(self):
        return reverse('projects:details', kwargs={'pk': self.pk})

    #TODO normalize to a field, update on signal
    def supporters_stats(self):
        money_supporters = set()
        time_supporters = set()
        money = 0
        time = datetime.timedelta(days=0)
        for money_support in self.moneysupport_set.all():
            money_supporters.add(money_support.user)
            money += money_support.leva
            
        for time_support in self.timesupport_set.all():
            time_supporters.add(time_support.user)
            time += time_support.duration()

        return len(money_supporters), money, len(time_supporters), time

    def total_supporters(self):
        supporters = set()
        for money_support in self.moneysupport_set.all():
            supporters.add(money_support.user)
        for time_support in self.timesupport_set.all():
            supporters.add(time_support.user)

        return len(supporters)

    def money_support(self):
        s = 0
        for money_support in self.moneysupport_set.filter(status__in=[Support.STATUS.accepted, Support.STATUS.delivered]):
            s += money_support.leva

        return s

    def things_fulfilled(self):
        s = 0
        money_support = self.money_support()
        for necessity in self.thingnecessity_set.all():
            accepted = necessity.accepted_support()
            s += accepted

        return s

    def things_still_needed(self):
        return self.things_needed() - self.things_fulfilled()

    def things_needed(self):
        s = 0
        for thing in self.thingnecessity_set.all():
            s += thing.count

        return s

    def time_fulfilled(self):
        s = 0
        for necessity in self.timenecessity_set.all():
            s += necessity.accepted_support()

        return s

    def time_still_needed(self):
        return self.time_needed() - self.time_fulfilled()

    def time_needed(self):
        s = 0
        for time in self.timenecessity_set.all():
            s += time.count

        return s
    
    def money_still_needed(self):
        return self.money_needed() - self.money_support()

    def money_needed(self):
        s = 0
        for thing in self.thingnecessity_set.all():
            s += thing.count * thing.price

        return s

    def money_support_percent(self):
        money_needed = self.money_needed()
        if money_needed == 0:
            return 0

        return int(100*self.money_support() / money_needed)

    def thing_support_percent(self):
        things_needed = self.things_needed()
        if things_needed == 0:
            return 0

        return int(100*self.things_fulfilled() / things_needed)

    def time_support_percent(self):
        time_needed = self.time_needed()
        if time_needed == 0:
            return 0

        return int(100*self.time_fulfilled() / time_needed)

    def recent_time_support(self):
        return self.timesupport_set.order_by('-status_since')

    def recent_money_support(self):
        return self.moneysupport_set.order_by('-status_since')

class Announcement(Timestamped, Activity):
    class Meta:
        rules_permissions = {
            "add": member_of_community,
            "delete": admin_of_community,
            "change": member_of_community,
            "view": rules.is_authenticated,
        }

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    text = models.TextField(verbose_name=_('announcement'))

    @property
    def activity_author_feed(self):
        return 'project'

    @property
    def activity_actor_attr(self):
        return self.project

    def get_absolute_url(self):
        return reverse('projects:announcement_details', kwargs={'pk': self.pk})

class Report(VoteModel, Timestamped, Activity):
    class Meta:
        rules_permissions = {
            "add": member_of_community,
            "delete": admin_of_community,
            "change": member_of_community,
            "view": rules.is_authenticated,
        }
    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    text = models.TextField()
    published_at = models.DateTimeField()

    @property
    def activity_author_feed(self):
        return 'project'

    @property
    def activity_actor_attr(self):
        return self.project

    def __str__(self):
        return self.published_at.isoformat()

    def get_absolute_url(self):
        return reverse('projects:report_details', kwargs={'pk': self.pk})

#TODO notify in feed
class TimeNecessity(Timestamped):
    class Meta:
        rules_permissions = {
            "add": member_of_community,
            "delete": member_of_community,
            "change": member_of_community,
            "view": rules.is_authenticated,
            "list": rules.is_authenticated,
        }

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=300)
    price = models.IntegerField()
    count = models.IntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name

    def still_needed(self):
        return self.count - self.accepted_support()

    def accepted_support(self):
        return self.supports.filter(status=Support.STATUS.accepted).count()

    def support_candidates(self):
        return self.supports.filter(status=Support.STATUS.review)

    def get_absolute_url(self):
        return reverse('projects:time_necessity_details', kwargs={'pk': self.pk})

#TODO notify in feed
class ThingNecessity(Timestamped):
    class Meta:
        rules_permissions = {
            "add": member_of_community,
            "delete": member_of_community,
            "change": member_of_community,
            "view": rules.is_authenticated,
            "list": rules.is_authenticated,
        }
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=300)
    price = models.IntegerField()
    count = models.IntegerField()

    def create_thing_support_from_unused_money_support(self):
        unused_money_support = list(filter(
            lambda s: not s.thingsupport_set.all().exists(),
            self.accepted_money_support()
            ))

        price = self.price
        use_supports = []

        
        if self.still_needed() == 0:
            return False

        for support in unused_money_support:
            use_supports.append(support)

            if support.leva < price:
                price -= support.leva
                continue

            remaining = support.leva - price
            while remaining >= 0:
                thing_support = self.supports.create(
                        price=self.price,
                        project=self.project,
                        user=self.project.community.admin,
                        comment='Auto generated',
                        status=Support.STATUS.accepted,
                        status_since = timezone.now(),
                )

                thing_support.from_money_supports.set(use_supports)
                use_supports = []
                price = self.price

                if remaining == 0:
                    break

                if self.still_needed() == 0:
                    self.money_supports.create(
                        leva=remaining,
                        project=self.project,
                        user=support.user,
                        comment='reminder from %d' % support.id,
                        status=Support.STATUS.review, # so that admin is forced to choose Necessity to spend it on
                        status_since = timezone.now(),
                        )
                    return True

                if remaining > 0:
                    use_supports.append(support)
                    saved_price = price
                    price -= remaining
                    remaining -= saved_price

        return True

    def __str__(self):
        return "%s" % self.name

    def still_needed(self):
        return self.count - self.accepted_support()

    def accepted_support(self):
        return self.supports.filter(status=Support.STATUS.accepted).count()

    def accepted_support_price(self):
        return self.accepted_support() * self.price

    def total_price(self):
        return self.count * self.price

    def total_price_still_needed(self):
        return self.still_needed() * self.price

    def accepted_money_support(self):
        return self.money_supports.filter(status=Support.STATUS.accepted).all()

    def accepted_money_support_leva(self):
        return sum(self.money_supports.filter(status=Support.STATUS.accepted).values_list('leva', flat=True))

    def support_candidates_count(self):
        return self.supports.filter(status=Support.STATUS.review).count() + self.money_supports.filter(status=Support.STATUS.review).count()

    def get_absolute_url(self):
        return reverse('projects:thing_necessity_details', kwargs={'pk': self.pk})

class Support(Timestamped):

    class Meta:
        abstract = True

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    
    comment = models.TextField(blank=True, verbose_name=_('Do you have a comment'))
    STATUS = Choices(
            'review',
            'delivered',
            'accepted',
            'declined',
            'expired')

    status = models.CharField(max_length=20, choices=STATUS, default=STATUS.review)
    status_since = models.DateTimeField(default=timezone.now)
    __original_status = None

    def __init__(self, *args, **kwargs):
        super(Support, self).__init__(*args, **kwargs)
        self.__original_status = self.status
    
    def save(self, *args, **kwargs):
        if self.status != self.__original_status:
            self.status_since = timezone.now()

        res = super(Support, self).save(*args, **kwargs)
        self.__original_status = self.status
        return res

    def delivery_expires(self):
        if not self.status == 'ccepted':
            return None

        return self.status_since + datetime.timedelta(days=30)

    def expired(self):
        if self.status == 'expired':
            return True

        expires = self.delivery_expires()
        if expires and expires < timezone.now():
            self.status = 'expired' 
            self.save()
            return True

        return False

    def set_accepted(self, accepted=True):
        if accepted is True:
            self.status = self.STATUS.accepted
        elif accepted is False:
            self.status = self.STATUS.declined
        else:
            self.status = self.STATUS.review

#        if accepted is not None:
#            self.accepted_at = timezone.now()

        self.save()

        return accepted

#TODO notify in feed
class MoneySupport(Support):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": myself & ~is_accepted,
            "change": (myself & ~is_accepted) | member_of_community,
            "view": myself | member_of_community,
            "accept": member_of_community,
            "mark_delivered": member_of_community,
            "list": member_of_community,
            "list-user": myself
        }

    necessity = models.ForeignKey(ThingNecessity, on_delete=models.PROTECT, related_name='money_supports', null=True, blank=True, verbose_name=_('Which necessity do you wish to donate to'))
    leva = models.FloatField(verbose_name=_('How much do you wish to donate'))
    anonymous = models.BooleanField(default=False, verbose_name=_('I wish to remain anonymous'), help_text=_('Check if you want your name to be hidden'))

    PAYMENT_METHODS = Choices(
            ('BankTransfer', _('Bank Transfer')),
            ('Revolut', _('Revolut')))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name=_('Choose a payment method'), default='Unspecified')

    def get_absolute_url(self):
        return reverse('projects:money_support_details', kwargs={'pk': self.pk})

    def get_type(self):
        return 'money'

    def set_accepted(self, accepted=True):
        super(MoneySupport, self).set_accepted(accepted)

        if accepted:
            if not self.necessity:
                raise RuntimeError('Expected necessity to be set when accepting money support')

            new_accepted = self.necessity.create_thing_support_from_unused_money_support()

            if new_accepted != accepted:
                return super(MoneySupport, self).set_accepted(None)

        return accepted

    def __str__(self):
        return "%s (%s)" % (self.user.first_name, self.leva) + (" for %s" % self.necessity if self.necessity else "")

#TODO notify in feed
class ThingSupport(Support):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": myself & ~is_accepted,
            "change": myself & ~is_accepted,
            "view": myself | member_of_community,
            "accept": member_of_community,
            "mark_delivered": member_of_community,
            "list": member_of_community,
            "list-user": myself
        }

    necessity = models.ForeignKey(ThingNecessity, on_delete=models.PROTECT, related_name='supports')
    price = models.IntegerField()
    from_money_supports = models.ManyToManyField(MoneySupport, blank=True)

    def get_absolute_url(self):
        return reverse('projects:thing_support_details', kwargs={'pk': self.pk})

    def get_type(self):
        return 'thing'

    def __str__(self):
        return "%s (%s)" % (self.user.first_name, self.necessity.name)

class Answer(Timestamped):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": myself & ~is_accepted,
            "change": myself & ~is_accepted,
            "view": myself | member_of_community,
            "list": myself & member_of_community
        }
        unique_together = ['project', 'question']

    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.PROTECT)
    answer = models.TextField(null=False, blank=True)

#TODO notify in feed
class TimeSupport(Support):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": myself & ~is_accepted,
            "change": (myself & ~is_accepted) | member_of_community,
            "view": myself | member_of_community,
            "accept": member_of_community,
            "mark_delivered": member_of_community,
            "list": member_of_community
        }
        unique_together = ['necessity', 'user']

    necessity = models.ForeignKey(TimeNecessity, on_delete=models.PROTECT, related_name='supports')
    price = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    def get_absolute_url(self):
        return reverse('projects:time_support_details', kwargs={'pk': self.pk})

    def get_type(self):
        return 'time'

    def duration(self):
        return (self.end_date - self.start_date).days

    def __str__(self):
        return "%s: %s" % (self.necessity, self.user.first_name)

    def ordered_answers(self):
        return self.answer_set.order_by('question__order')


class QuestionPrototype(Timestamped):
    class Meta:
        rules_permissions = {
            "add": rules.always_deny,
            "delete": rules.always_deny,
            "change": rules.always_deny,
            "view": rules.always_allow,
            "list": rules.always_allow 
            }

    text_bg = models.CharField(max_length=100, unique=True)
    text_en = models.CharField(max_length=100, unique=True)
    TYPES = Choices('CharField', 'TextField', 'FileField', 'ChoiceField', 'Necessities')

    type = models.CharField(max_length=20, choices=TYPES)
    order = models.IntegerField()
    required = models.BooleanField(default=True)

    def __str__(self):
        return self.text_bg

class Question(Timestamped):
    class Meta:
        rules_permissions = {
            "add": member_of_community,
            "delete": member_of_community,
            "change": member_of_community,
            "view": rules.always_allow,
            "list": rules.always_allow 
            }
        unique_together=['prototype', 'project']

    prototype = models.ForeignKey(QuestionPrototype, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    order = models.IntegerField()

    def __str__(self):
        return "%s. %s%s" % (self.order, self.prototype, ('*' if self.required else ''))
    
    def text(self):
        return getattr(self.prototype, 'text_%s' % get_language())
