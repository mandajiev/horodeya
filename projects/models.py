from django.utils import timezone
import datetime

from django.db import models
from django.utils import timezone
from django.urls import reverse

from django.core.validators import MaxValueValidator

from django.contrib.auth.models import AbstractUser

import rules
from rules.contrib.models import RulesModelBase, RulesModelMixin

from vote.models import VoteModel, UP, DOWN

from stream_django.activity import Activity

def determine_legal_entity(object):
    if isinstance(object, Project):
        return object.legal_entity
    elif isinstance(object, Report) or isinstance(object, Support):
        return object.project.legal_entity

    return object

@rules.predicate
def member_of_legal_entity(user, object):
    return user.member_of(determine_legal_entity(object).id)

@rules.predicate
def admin_of_legal_entity(user, object):
    return user == determine_legal_entity(object).admin

@rules.predicate
def myself(user, user2):
    return user == user2

@rules.predicate
def has_a_legal_entity(user):
    return user.legal_entities.count() > 0

@rules.predicate
def is_accepted(support):
    return support.accepted

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

class LegalEntity(Timestamped):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": admin_of_legal_entity,
            "change": admin_of_legal_entity,
            "view": rules.is_authenticated,
            "leave": member_of_legal_entity & ~admin_of_legal_entity
        }

    name = models.CharField(max_length=100)
    text = models.TextField()
    bulstat = models.DecimalField(blank=True, max_digits=20, decimal_places=0)
    email = models.EmailField()
    phone = models.DecimalField(max_digits=20, decimal_places=0)
    admin = models.ForeignKey('User', on_delete=models.PROTECT)
    payment = models.TextField()
    bal = models.IntegerField(default=20, validators=[MaxValueValidator(100)])

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:legal_details', kwargs={'pk': self.pk})

class User(AbstractUser, RulesModelMixin, metaclass=RulesModelBase):
    class Meta:
        rules_permissions = {
            "add": rules.always_allow,
            "delete": rules.always_deny,
            "change": myself,
            "view": rules.is_authenticated,
        }

    legal_entities = models.ManyToManyField(LegalEntity)
    bal = models.IntegerField(default=20, validators=[MaxValueValidator(100)])

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

    def get_absolute_url(self):
        return reverse('account', kwargs={'pk': self.pk})

    def member_of(self, legal_entity_pk):
        return self.legal_entities.filter(pk=legal_entity_pk).exists()

    def total_support_count(self):
        return self.moneysupport_set.count() + self.timesupport_set.count()

    def total_votes_count(self):
        return len(Report.votes.all(self.pk, UP)) + len(Report.votes.all(self.pk, DOWN))

#TODO notify user on new project added
class Project(Timestamped):
    class Meta:
        rules_permissions = {
            "add": admin_of_legal_entity,
            "delete": admin_of_legal_entity,
            "change": member_of_legal_entity,
            "view": rules.always_allow,
        }

    TYPES = [
        ('b', 'business'),
        ('c', 'cause'),
    ]
    type = models.CharField(max_length=1, choices=TYPES)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=300)
    text = models.TextField()
    published = models.BooleanField()
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE)
    leva_needed = models.FloatField(null=True, blank=True)
    budget_until = models.DateField(null=True, blank=True)

    def key(self):
        return 'project-%d' % self.id

    def __str__(self):
        return self.name

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
        for money_support in self.moneysupport_set.all():
            s += money_support.leva

        return s

    def support_percent(self):
        if not self.leva_needed:
            return 0

        return int(100*self.money_support() / self.leva_needed)

class Announcement(Timestamped, Activity):
    class Meta:
        rules_permissions = {
            "add": member_of_legal_entity,
            "delete": admin_of_legal_entity,
            "change": member_of_legal_entity,
            "view": rules.is_authenticated,
        }

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    text = models.TextField(verbose_name='announcement')

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
            "add": member_of_legal_entity,
            "delete": admin_of_legal_entity,
            "change": member_of_legal_entity,
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

class Support(Timestamped):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": myself & ~is_accepted,
            "change": myself & ~is_accepted,
            "view": myself | member_of_legal_entity,
            "accept": member_of_legal_entity,
            "mark_delivered": member_of_legal_entity,
            "list": member_of_legal_entity
        }

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    
    accepted = models.BooleanField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    delivered = models.BooleanField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def delivery_expires(self):
        if not self.accepted_at:
            return None

        return self.accepted_at + datetime.timedelta(days=30)

    def expired(self):
        if self.delivered == False:
            return True
        expires = self.delivery_expires()
        if expires and expires < timezone.now():
            self.delivered = False
            self.save()
            return True

        return False

    class Meta:
        abstract = True

class MoneySupport(Support):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": myself & ~is_accepted,
            "change": myself & ~is_accepted,
            "view": myself | member_of_legal_entity,
            "accept": member_of_legal_entity,
            "mark_delivered": member_of_legal_entity,
            "list": member_of_legal_entity,
            "list-user": myself
        }
    leva = models.FloatField()

    def get_absolute_url(self):
        return reverse('projects:msupport_details', kwargs={'pk': self.pk})

    def get_type(self):
        return 'm'

    def __str__(self):
        return "%s-%.2f" % (self.project, self.leva)

class TimeSupport(Support):
    class Meta:
        rules_permissions = {
            "add": rules.is_authenticated,
            "delete": myself & ~is_accepted,
            "change": myself & ~is_accepted,
            "view": myself | member_of_legal_entity,
            "accept": member_of_legal_entity,
            "mark_delivered": member_of_legal_entity,
            "list": member_of_legal_entity
        }

    start_date = models.DateField()
    end_date = models.DateField()
    note = models.TextField()

    def get_absolute_url(self):
        return reverse('projects:tsupport_details', kwargs={'pk': self.pk})

    def get_type(self):
        return 't'

    def duration(self):
        return self.end_date - self.start_date
