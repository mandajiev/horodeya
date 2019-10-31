from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Project, User
from vote.models import Vote

# Register your models here.

admin.site.register(Project)
admin.site.register(User, UserAdmin)
admin.site.register(Vote)
