from functools import wraps
from django.http import HttpResponseNotAllowed, HttpResponseForbidden, HttpResponse
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django import get_version as django_version
from decorator import decorator

from datetime import datetime, timedelta

__version__ = '0.2'

def get_version():
    return __version__

def format_error(error):
    return u"Piston/%s (Django %s) crash report:\n\n%s" % \
        (get_version(), django_version(), error)

def create_reply(message, status=200):
    return HttpResponse(message, status=status)

class rc(object):
    """
    Status codes.
    """
    ALL_OK = create_reply('OK', status=200)
    CREATED = create_reply('Created', status=201)
    DELETED = create_reply('', status=204) # 204 says "Don't send a body!"
    BAD_REQUEST = create_reply('Bad Request', status=400)
    FORBIDDEN = create_reply('Forbidden', status=401)
    DUPLICATE_ENTRY = create_reply('Conflict/Duplicate', status=409)
    NOT_HERE = create_reply('Gone', status=410)
    NOT_IMPLEMENTED = create_reply('Not Implemented', status=501)
    THROTTLED = create_reply('Throttled', status=503)
    
class FormValidationError(Exception):
    def __init__(self, form):
        self.form = form

class HttpStatusCode(Exception):
    def __init__(self, message, code=200):
        self.message = message
        self.code = code

def validate(v_form, operation='POST'):
    @decorator
    def wrap(f, self, request, *a, **kwa):
        form = v_form(getattr(request, operation))
    
        if form.is_valid():
#            kwa.update({ 'form': form })
            return f(self, request, *a, **kwa)
        else:
            raise FormValidationError(form)
    return wrap

def throttle(max_requests, timeout=60*60, extra=''):
    """
    Simple throttling decorator, caches
    the amount of requests made in cache.
    
    If used on a view where users are required to
    log in, the username is used, otherwise the
    IP address of the originating request is used.
    
    Parameters::
     - `max_requests`: The maximum number of requests
     - `timeout`: The timeout for the cache entry (default: 1 hour)
    """
    @decorator
    def wrap(f, self, request, *args, **kwargs):
        if request.user.is_authenticated():
            ident = request.user.username
        else:
            ident = request.META.get('REMOTE_ADDR', None)
    
        if hasattr(request, 'throttle_extra'):
            """
            Since we want to be able to throttle on a per-
            application basis, it's important that we realize
            that `throttle_extra` might be set on the request
            object. If so, append the identifier name with it.
            """
            ident += ':%s' % str(request.throttle_extra)
        
        if ident:
            """
            Preferrably we'd use incr/decr here, since they're
            atomic in memcached, but it's in django-trunk so we
            can't use it yet. If someone sees this after it's in
            stable, you can change it here.
            """
            ident += ':%s' % extra
    
            now = datetime.now()
            ts_key = 'throttle:ts:%s' % ident
            timestamp = cache.get(ts_key)
            offset = now + timedelta(seconds=timeout)
    
            if timestamp and timestamp < offset:
                t = rc.THROTTLED
                wait = timeout - (offset-timestamp).seconds
                t.content = 'Throttled, wait %d seconds.' % wait
                
                return t
                
            count = cache.get(ident, 1)
            cache.set(ident, count+1)
            
            if count >= max_requests:
                cache.set(ts_key, offset, timeout)
                cache.set(ident, 1)
    
        return f(self, request, *args, **kwargs)
    return wrap

def coerce_put_post(request):
    if request.method == "PUT":
        request.method = "POST"
        request._load_post_and_files()
        request.method = "PUT"
        request.PUT = request.POST
        del request._post

