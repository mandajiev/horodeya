from django.utils import timezone
import datetime

from django.db import models
from django.utils import timezone
from django.urls import reverse

from django.core.validators import MaxValueValidator

from django.contrib.auth.models import AbstractUser

from vote.models import VoteModel

class Timestamped(models.Model):
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
    name = models.CharField(max_length=100)
    bulstat = models.DecimalField(blank=True, max_digits=20, decimal_places=0)
    email = models.EmailField()
    phone = models.DecimalField(max_digits=20, decimal_places=0)
    admin = models.ForeignKey('User', on_delete=models.PROTECT)
    payment = models.TextField()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:legal_details', kwargs={'pk': self.pk})

class User(AbstractUser):
    legal_entities = models.ManyToManyField(LegalEntity)
    bal = models.IntegerField(default=20, validators=[MaxValueValidator(100)])

    def get_absolute_url(self):
        return reverse('account', kwargs={'pk': self.pk})

    def member_of(self, legal_entity_pk):
        return self.legal_entities.filter(pk=legal_entity_pk).exists()

class Project(Timestamped):
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
    bal = models.IntegerField(default=20, validators=[MaxValueValidator(100)])

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

class Report(VoteModel, Timestamped):
    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    text = models.TextField()
    published_at = models.DateTimeField()

    def __str__(self):
        return self.published_at.isoformat()

    def get_absolute_url(self):
        return reverse('projects:report_details', kwargs={'pk': self.pk})

class Support(Timestamped):
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
    leva = models.FloatField()

    def get_absolute_url(self):
        return reverse('projects:msupport_details', kwargs={'pk': self.pk})

    def get_type(self):
        return 'm'

    def __str__(self):
        return "%s-%.2f" % (self.project, self.leva)

class TimeSupport(Support):
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.TextField()

    def get_absolute_url(self):
        return reverse('projects:tsupport_details', kwargs={'pk': self.pk})

    def get_type(self):
        return 't'

    def duration(self):
        return self.end_date - self.start_date
