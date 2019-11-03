from django.db import models
from django import forms
from django.contrib.auth.models import AbstractUser
from django.shortcuts import render

from wagtail.core.models import Page, Orderable
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel

from projects.models import Project

## TODO how to add anitial pages
#class HorodeyaPage(Page):
#    def get_context(self, request):
#        context = super().get_context(request)
#
#        context['menu_items'] = Page.objects.live().in_menu() #TODO cache
#        return context
#
#    class Meta:
#        abstract = True

class HomePage(Page):
    body = StreamField([
        ('text', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('action', blocks.StructBlock([
            ('heading', blocks.CharBlock()),
            ('text', blocks.RichTextBlock()),
            ('page', blocks.PageChooserBlock())], 
            template='home/blocks/action.html')),
        ('action_register', blocks.StructBlock([
            ('text', blocks.RichTextBlock())], 
            template='home/blocks/action_register.html')),
    ])

    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]

class List(Page):
    body = RichTextField(blank=True)
    type = models.CharField(max_length=1, choices=Project.TYPES)

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
        FieldPanel('type'),
    ]

    def serve(self, request):
        return render(request, 'home/list.html', {
            'page': self,
            'items': Project.objects.filter(type=self.type).order_by('-bal'),
        })
