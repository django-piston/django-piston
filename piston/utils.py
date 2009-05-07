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

class Mimer(object):
    TYPES = dict()
    
    def __init__(self, request):
        self.request = request
        
    def is_multipart(self):
        return 'Content-Disposition: form-data;' in self.request.raw_post_data

    def loader_for_type(self, ctype):
        """
        Gets a function ref to deserialize content
        for a certain mimetype.
        """
        for loadee, mimes in Mimer.TYPES.iteritems():
            if ctype in mimes:
                return loadee

    def content_type(self):
        return self.request.META.get('CONTENT_TYPE')

    def translate(self):
        """
        Will look at the `Content-type` sent by the client, and maybe
        deserialize the contents into the format they sent. This will
        work for JSON, YAML, XML and Pickle. Since the data is not just
        key-value (and maybe just a list), the data will be placed on
        `request.data` instead, and the handler will have to read from
        there.
        
        It will also set `request.mimetype` so the handler has an easy
        way to tell what's going on. `request.mimetype` will always be
        None for multipart form data (what your browser sends.)
        """    
        ctype = self.content_type()
        
        if not self.is_multipart() and ctype:
            loadee = self.loader_for_type(ctype)
            
            try:
                self.request.content_type = ctype
                self.request.data = loadee(self.request.raw_post_data)
                
                # Reset both POST and PUT from request, as its
                # misleading having their presence around.
                self.request.POST = self.request.PUT = dict()
            except TypeError:
                return rc.BAD_REQUEST # TODO: Handle this in super
            except Exception, e:
                raise
                
        return self.request
                
    @classmethod
    def register(cls, loadee, types):
        cls.TYPES[loadee] = types
        
    @classmethod
    def unregister(cls, loadee):
        return cls.TYPES.pop(loadee)

def translate_mime(request):
    request = Mimer(request).translate()
    
def require_mime(*mimes):
    """
    Decorator requiring a certain mimetype. There's a nifty
    helper called `require_extended` below which requires everything
    we support except for post-data via form.
    """
    @decorator
    def wrap(f, self, request, *args, **kwargs):
        m = Mimer(request)
        realmimes = set()

        rewrite = { 'json':   'application/json',
                    'yaml':   'application/x-yaml',
                    'xml':    'text/xml',
                    'pickle': 'application/python-pickle' }

        for idx, mime in enumerate(mimes):
            realmimes.add(rewrite.get(mime, mime))

        if not m.content_type() in realmimes:
            return rc.BAD_REQUEST

        return f(self, request, *args, **kwargs)
    return wrap

require_extended = require_mime('json', 'yaml', 'xml', 'pickle')
    