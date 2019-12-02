from stream_django.feed_manager import feed_manager

def stream_token(request):

    if request.user.is_authenticated:
        stream_token = feed_manager.get_notification_feed(request.user.id).get_readonly_token()
    else:
        stream_token = None

    return {'stream_token': stream_token}
