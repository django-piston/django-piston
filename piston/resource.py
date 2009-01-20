from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseForbidden
from django.views.decorators.vary import vary_on_headers
from emitters import Emitter
from handler import typemapper
from utils import coerce_put_post, FormValidationError, HttpStatusCode

class NoAuthentication(object):
    """
    Authentication handler that always returns
    True, so no authentication is needed, nor
    initiated (`challenge` is missing.)
    """
    def is_authenticated(self, request):
        return True

class Resource(object):
    """
    Resource. Create one for your URL mappings, just
    like you would with Django. Takes one argument,
    the handler. The second argument is optional, and
    is an authentication handler. If not specified,
    `NoAuthentication` will be used by default.
    """
    callmap = { 'GET': 'read', 'POST': 'create', 
                'PUT': 'update', 'DELETE': 'delete' }
    
    def __init__(self, handler, authentication=None):
        if not callable(handler):
            raise AttributeError, "Handler not callable."
        
        self.handler = handler()
        
        if not authentication:
            self.authentication = NoAuthentication()
        else:
            self.authentication = authentication
    
    @vary_on_headers('Authorization')
    def __call__(self, request, *args, **kwargs):
        """
        NB: Sends a `Vary` header so we don't cache requests
        that are different (OAuth stuff in `Authorization` header.)
        """
        if not self.authentication.is_authenticated(request):
            if self.handler.anonymous and callable(self.handler.anonymous):
                handler = self.handler.anonymous()
            else:
                return self.authentication.challenge()
        else:
            handler = self.handler
        
        rm = request.method.upper()
        
        # Django's internal mechanism doesn't pick up
        # PUT request, so we trick it a little here.
        if rm == "PUT":
            coerce_put_post(request)
        
        if not rm in handler.allowed_methods:
            return HttpResponseNotAllowed(handler.allowed_methods)
        
        meth = getattr(handler, Resource.callmap.get(rm), None)
        
        if not meth:
            raise Http404
        
        # Clean up the request object a bit, since we might
        # very well have `oauth_`-headers in there, and we
        # don't want to pass these along to the handler.
        request = self.cleanup_request(request)
        
        try:
            result = meth(request, *args, **kwargs)
        except FormValidationError, errors:
            return HttpResponse("errors: %r" % errors)
        except Exception, e:
            result = e
        
        emitter, ct = Emitter.get(request.GET.get('format', 'json'))
        srl = emitter(result, typemapper, handler.fields)

        try:
            return HttpResponse(srl.render(request), mimetype=ct)
        except HttpStatusCode, e:
            return HttpResponse(e.message, status=e.code)

    @staticmethod
    def cleanup_request(request):
        """
        Removes `oauth_` keys from various dicts on the
        request object, and returns the sanitized version.
        """
        for method_type in [ 'GET', 'PUT', 'POST', 'DELETE' ]:
            block = getattr(request, method_type, { })

            if True in [ k.startswith("oauth_") for k in block.keys() ]:
                sanitized = block.copy()
                
                for k in sanitized.keys():
                    if k.startswith("oauth_"):
                        sanitized.pop(k)
                        
                setattr(request, method_type, sanitized)

        return request
        
