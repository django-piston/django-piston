typemapper = { }

class HandlerMetaClass(type):
    """
    Metaclass that keeps a registry of class -> handler
    mappings.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        
        if hasattr(new_cls, 'model'):
            typemapper[new_cls.model] = new_cls
        
        return new_cls

class AnonymousBaseHandler(object):
    """
    Anonymous handler.
    """
    allowed_methods = ('GET',)
    
class BaseHandler(object):
    """
    Basehandler that gives you CRUD for free.
    You are supposed to subclass this for specific
    functionality.
    
    All CRUD methods (`read`/`update`/`create`/`delete`)
    receive a request as the first argument from the
    resource. Use this for checking `request.user`, etc.
    """
    __metaclass__ = HandlerMetaClass
    
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    anonymous = False
    exclude = ( 'id' )
    fields =  ( )
    
    def flatten_dict(self, dct):
        return dict([ (str(k), dct.get(k)) for k in dct.keys() ])
    
    def has_model(self):
        return hasattr(self, 'model')
    
    def value_from_tuple(tu, name):
        for int_, n in tu:
            if n == name:
                return int_
        return None
    
    def exists(self, **kwargs):
        if not self.has_model():
            raise NotImplementedError
        
        try:
            self.model.objects.get(**kwargs)
            return True
        except self.model.DoesNotExist:
            return False
    
    def read(self, request, *args, **kwargs):
        if not self.has_model():
            raise NotImplementedError
        
        return self.model.objects.filter(*args, **kwargs)
    
    def create(self, request, *args, **kwargs):
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
    
    def update(self, request, *args, **kwargs):
        if not self.has_model():
            raise NotImplementedError
        
        inst = self.model.objects.get(*args, **kwargs)
        print "must update instance", inst, "with", request.PUT
        
        return "I can't do this yet."
    
    def delete(self, request, *args, **kwargs):
        if not self.has_model():
            raise NotImplementedError
        
        return "I can't do this yet."

