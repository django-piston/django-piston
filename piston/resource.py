"""
Piston resource.
"""
from django.http import HttpResponse, Http404
from emitters import Emitter
from handler import typemapper

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
        meth = getattr(self.handler, Resource.callmap.get(rm), None)
        format = request.GET.get('format', 'json')
        
        if not meth:        
            raise Http404

        result = meth(request)
        emitter, ct = Emitter.get(format)
        srl = emitter(result, typemapper)
        
        return HttpResponse(srl.render(), mimetype=ct)
