import django.dispatch

entry_request_started = django.dispatch.Signal(providing_args=['request'])
