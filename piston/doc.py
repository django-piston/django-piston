import inspect, handler

def generate_doc(handler_cls):
    """
    Returns a `HandlerDocumentation` object
    for the given handler. Use this to generate
    documentation for your API.
    """
    if not type(handler_cls) is handler.HandlerMetaClass:
        raise ValueError("Give me handler, not %s" % type(handler_cls))
        
    return HandlerDocumentation(handler_cls)
    
class HandlerMethod(object):
    def __init__(self, method, stale=False):
        self.method = method
        self.stale = stale
        
    def iter_args(self):
        args, _, _, defaults = inspect.getargspec(self.method)

        for idx, arg in enumerate(args):
            if arg in ('self', 'request'):
                continue

            didx = len(args)-idx

            if defaults and len(defaults) >= didx:
                yield (arg, str(defaults[-didx]))
            else:
                yield (arg, None)
        
    def get_signature(self, parse_optional=True):
        spec = ""

        for argn, argdef in self.iter_args():
            spec += argn
            
            if argdef:
                spec += '=%s' % argdef
            
            spec += ', '
            
        spec = spec.rstrip(", ")
        
        if parse_optional:
            return spec.replace("=None", "=<optional>")
            
        return spec

    signature = property(get_signature)
        
    def get_doc(self):
        return inspect.getdoc(self.method)
    
    doc = property(get_doc)
    
    def get_name(self):
        return self.method.__name__
        
    name = property(get_name)
    
    def __repr__(self):
        return "<Method: %s>" % self.name
    
class HandlerDocumentation(object):
    def __init__(self, handler):
        self.handler = handler
        
    def get_methods(self, include_default=False):
        for method in "read create update delete".split():
            met = getattr(self.handler, method)
            stale = inspect.getmodule(met) is handler

            if met and (not stale or include_default):
                yield HandlerMethod(met, stale)
        
    @property
    def is_anonymous(self):
        return False

    @property
    def model(self):
        return getattr(self, 'model', None)
    
    @property
    def name(self):
        return self.handler.__name__
    
    def __repr__(self):
        return u'<Documentation for "%s">' % self.name
