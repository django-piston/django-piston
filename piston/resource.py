"""
Piston resource.
"""
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseForbidden
from emitters import Emitter
from handler import typemapper
from utils import coerce_put_post, FormValidationError

class NoAuthentication(object):
    def is_authenticated(self, request):
        return True

class Resource(object):
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
        
    def __call__(self, request, *args, **kwargs):

        if not self.authentication.is_authenticated(request):
            return self.authentication.challenge()

        rm = request.method.upper()
        
        # Django's internal mechanism doesn't pick up
        # PUT request, so we trick it a little here.
        if rm == "PUT": coerce_put_post(request)

        if not rm in self.handler.allowed_methods:
            return HttpResponseNotAllowed(self.handler.allowed_methods)

        meth = getattr(self.handler, Resource.callmap.get(rm), None)
        format = request.GET.get('format', 'json')
        
        if not meth:        
            raise Http404

        try:
            result = meth(request, *args, **kwargs)
        except FormValidationError, errors:
            return HttpResponse("errors: %r" % errors)
        except Exception, e:
            result = e
        
        emitter, ct = Emitter.get(format)
        srl = emitter(result, typemapper)
        
        return HttpResponse(srl.render(), mimetype=ct)
