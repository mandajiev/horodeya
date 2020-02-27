from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import UpdateView
from projects.models import User
from django.http import JsonResponse

from stream_django.feed_manager import feed_manager
from stream_django.enrich import Enrich
from django.conf import settings

def account(request, pk=None):
    if pk:
        account = get_object_or_404(User, pk=pk)
    else:
        account = request.user 
    return render(request, 'home/account.html', { 'object': account, 'oidc_user_account': settings.OIDC_USER_ACCOUNT } )

def notifications(request):
    user = request.user 

    notification_feed = feed_manager.get_notification_feed(user.id)
    notification_stats = notification_feed.get(limit=10, mark_seen=True)
    enricher = Enrich()
    notifications = enricher.enrich_aggregated_activities(notification_stats['results'])

    return render(request, 'activity/aggregated/report.html', {'notifications': notifications})

