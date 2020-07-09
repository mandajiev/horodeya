from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Project, Community, User, MoneySupport, TimeSupport, ThingSupport, Announcement, QuestionPrototype, Question, Answer, Report, DonatorData, LegalEntityDonatorData, BugReport
from vote.models import Vote

# Register your models here.

admin.site.register(Project)
admin.site.register(Community)
admin.site.register(User, UserAdmin)
admin.site.register(Vote)
admin.site.register(MoneySupport)
admin.site.register(TimeSupport)
admin.site.register(ThingSupport)
admin.site.register(Announcement)
admin.site.register(QuestionPrototype)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Report)
admin.site.register(DonatorData)
admin.site.register(LegalEntityDonatorData)
admin.site.register(BugReport)
