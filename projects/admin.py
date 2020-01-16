from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Project, LegalEntity, User, MoneySupport, TimeSupport, ThingSupport, Announcement
from vote.models import Vote

# Register your models here.

admin.site.register(Project)
admin.site.register(LegalEntity)
admin.site.register(User, UserAdmin)
admin.site.register(Vote)
admin.site.register(MoneySupport)
admin.site.register(TimeSupport)
admin.site.register(ThingSupport)
admin.site.register(Announcement)
