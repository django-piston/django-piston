typemapper = { }

class HandlerType(type):
    def __init__(cls, name, bases, dct):
        model = dct.get('model', None)
        
        if model:
            typemapper[model] = cls
        
        return super(HandlerType, cls).__init__(name, bases, dct)

class BaseHandler(object):
    __metaclass__ = HandlerType

    def flatten_dict(self, dct):
        return dict([ (str(k), dct.get(k)) for k in dct.keys() ])

    def has_model(self):
        return hasattr(self, 'model')

    def read(self, request, *a, **kwa):
        if not self.has_model():
            raise NotImplementedError

        return self.model.objects.filter(*a, **kwa)
        
    def create(self, request, *a, **kwa):
        if not self.has_model():
            raise NotImplementedError
    
        attrs = self.flatten_dict(request.POST)

        try:
            inst = self.model.objects.get(**attrs)
            raise ValueError("Already exists.")
        except self.model.DoesNotExist:
            inst = self.model(attrs)
            inst.save()

            return inst        
                        
    def update(self, request, *a, **kwa):
        if not self.has_model():
            raise NotImplementedError
            
        inst = self.model.objects.get(*a, **kwa)
        print "must update instance", inst, "with", request.POST
