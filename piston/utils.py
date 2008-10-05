from django.http import HttpResponseNotAllowed, HttpResponseForbidden
from django.core.urlresolvers import reverse

class HttpForbidden(HttpResponseForbidden):
    pass

class FormValidationError(Exception):
    pass

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
        
def resource_uri(f):
    def wrap(self, instance):
        url_id, args = f(self, instance)
        try:
            return reverse(url_id, args=args)
        except Exception, e:
            return None
    return wrap
