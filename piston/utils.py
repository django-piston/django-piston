from django.http import HttpResponseNotAllowed, HttpResponseForbidden, HttpResponse
from django.core.urlresolvers import reverse

def create_reply(message, status=200):
    return HttpResponse(message, status=status)

class rc(object):
    """
    Status codes.
    """
    ALL_OK = create_reply('OK', status=200)
    CREATED = create_reply('Created', status=201)
    DELETED = create_reply('No Content', status=204)
    FORBIDDEN = create_reply('Forbidden', status=401)
    DUPLICATE_ENTRY = create_reply('Conflict', status=409)
    NOT_HERE = create_reply('Gone', status=410)
    NOT_IMPLEMENTED = create_reply('Not Implemented', status=501)
    
class FormValidationError(Exception):
    pass

class HttpStatusCode(Exception):
    def __init__(self, message, code=200):
        self.message = message
        self.code = code

def validate(form, operation='POST'):
    def dec(func):
        def wrap(self, request, *a, **kwa):
            f = form(getattr(request, operation))

            if f.is_valid():
                kwa.update({'form':f})
                return func(self, request, *a, **kwa)
            else:
                raise FormValidationError(f.errors)
                                
        return wrap
    return dec

def coerce_put_post(request):
    if request.method == "PUT":
        request.method = "POST"
        request._load_post_and_files()
        request.method = "PUT"
        request.PUT = request.POST
        del request._post

