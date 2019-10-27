import datetime

from django.db import models
from django.utils import timezone
from django.urls import reverse

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator

class Timestamped(models.Model):
    created_at = models.DateTimeField(editable=False)
    edited_at = models.DateTimeField(editable=False)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()

        self.edited_at = timezone.now()
        return super(Timestamped, self).save(*args, **kwargs)

    class Meta:
        abstract = True

class LegalEntity(Timestamped):
    name = models.CharField(max_length=100)
    bulstat = models.DecimalField(blank=True, max_digits=20, decimal_places=0)
    email = models.EmailField()
    phone = models.DecimalField(max_digits=20, decimal_places=0)

class HorodeyaUser(Timestamped):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, blank=True)
    bal = models.IntegerField(default=20, validators=[MaxValueValidator(100)])

class Project(Timestamped):
    TYPES = [
        ('b', 'business'),
        ('c', 'cause'),
    ]
    type = models.CharField(max_length=1, choices=TYPES)
    name = models.CharField(max_length=50)
    description = models.TextField()
    published = models.BooleanField()
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, blank=True, default=None)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:details', kwargs={'pk': self.pk})

class Report(Timestamped):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    text = models.TextField()
    published_at = models.DateTimeField()

    def __str__(self):
        return self.published_at.isoformat()

