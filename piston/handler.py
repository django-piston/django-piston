typemapper = { }

class HandlerType(type):
    def __init__(cls, name, bases, dct):
        model = dct.get('model', None)
        
        if model:
            typemapper[model] = cls
        
        return super(HandlerType, cls).__init__(name, bases, dct)

class BaseHandler(object):
    __metaclass__ = HandlerType

    def has_model(self):
        return hasattr(self, 'model')

    def read(self, request, *a, **kwa):
        if not self.has_model():
            return NotImplementedError

        return self.model.objects.filter(*a, **kwa)
