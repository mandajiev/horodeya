from django.db import models
from django import forms
from django.contrib.auth.models import AbstractUser
from django.shortcuts import render

from wagtail.core.models import Page, Orderable
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel

from stream_django.feed_manager import feed_manager
from stream_django.enrich import Enrich

from projects.models import Project


class HomePage(Page):
    body = StreamField([
        ('text', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('action', blocks.StructBlock([
            ('heading1', blocks.CharBlock()),
            ('heading2', blocks.CharBlock()),
            ('text1', blocks.RichTextBlock()),
            ('text2', blocks.RichTextBlock()),
            ('page1', blocks.PageChooserBlock()),
            ('page2', blocks.PageChooserBlock()),
        ],
            template='home/blocks/action.html')),
        ('action_register', blocks.StructBlock([
            ('text', blocks.RichTextBlock())],
            template='home/blocks/action_register.html')),
    ])

    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]

    def serve(self, request):
        # user = request.user

        # if user.is_authenticated:
        #     feed = feed_manager.get_feed('timeline', user.id)
        # else:
        #     feed = feed_manager.get_feed('timeline', 0)

        # enricher = Enrich()
        # timeline = enricher.enrich_activities(feed.get(limit=25)['results'])

        return render(request, 'home/home_page.html', {
            'page': self,
            # 'timeline': timeline,
        })


class AboutUs(Page):

    body = StreamField([
        ('text', blocks.TextBlock()),
        ('heroImage', ImageChooserBlock()),
        ('person', blocks.StructBlock([
            ('name', blocks.TextBlock()),
            ('role', blocks.TextBlock()),
            ('info', blocks.TextBlock()),
            ('photo', ImageChooserBlock()),
            ('order', blocks.IntegerBlock()),
        ],
            template='home/blocks/person.html'))])

    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]


class List(Page):
    body = RichTextField(blank=True)
    type = models.CharField(max_length=20, choices=Project.TYPES)

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
        FieldPanel('type'),
    ]

    def serve(self, request):
        return render(request, 'home/list.html', {
            'page': self,
            'items': Project.objects.filter(verified_status='accepted').order_by('-community__bal'),
        })


class TermsAndConditions(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
    ]


class LearnMore(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
    ]
