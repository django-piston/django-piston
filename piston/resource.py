"""
Piston resource.
"""
from django.http import HttpResponse, Http404
from emitters import Emitter

class Resource(object):
    callmap = { 'GET': 'read', 'POST': 'create', 
                'PUT': 'update', 'DELETE': 'delete' }

    def __init__(self, handler, authentication=None):
        if not callable(handler):
            raise AttributeError, "Handler not callable."

        self.handler = handler()
        self.authentication = authentication
        
    def __call__(self, request, *args, **kwargs):
        rm = request.method.upper()        
        meth = getattr(self.handler, Resource.callmap.get(rm), None)
        format = request.GET.get('format', 'json')
        
        if not meth:        
            raise Http404

        result, fields = meth(request)
        emitter, ct = Emitter.get(format)
        srl = emitter(result, fields)
        
        return HttpResponse(srl.render(), mimetype=ct)
