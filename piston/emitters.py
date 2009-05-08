import types, decimal, types, re, inspect

try:
    # yaml isn't standard with python.  It shouldn't be required if it
    # isn't used.
    import yaml
except ImportError:
    yaml = None

from django.db.models.query import QuerySet
from django.db.models import Model, permalink
from django.utils import simplejson
from django.utils.xmlutils import SimplerXMLGenerator
from django.utils.encoding import smart_unicode
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.http import HttpResponse

from utils import HttpStatusCode, Mimer

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

try:
    import cPickle as pickle
except ImportError:
    import pickle

class Emitter(object):
    """
    Super emitter. All other emitters should subclass
    this one. It has the `construct` method which
    conveniently returns a serialized `dict`. This is
    usually the only method you want to use in your
    emitter. See below for examples.
    """
    EMITTERS = { }

    def __init__(self, payload, typemapper, handler, fields=(), anonymous=True):
        self.typemapper = typemapper
        self.data = payload
        self.handler = handler
        self.fields = fields
        self.anonymous = anonymous
        
        if isinstance(self.data, Exception):
            raise
    
    def construct(self):
        """
        Recursively serialize a lot of types, and
        in cases where it doesn't recognize the type,
        it will fall back to Django's `smart_unicode`.
        
        Returns `dict`.
        """
        def _any(thing, fields=()):
            """
            Dispatch, all types are routed through here.
            """
            ret = None
            
            if isinstance(thing, (tuple, list, QuerySet)):
                ret = _list(thing)
            elif isinstance(thing, dict):
                ret = _dict(thing)
            elif isinstance(thing, decimal.Decimal):
                ret = str(thing)
            elif isinstance(thing, Model):
                ret = _model(thing, fields=fields)
            elif isinstance(thing, HttpResponse):
                raise HttpStatusCode(thing.content, code=thing.status_code)
            elif isinstance(thing, types.FunctionType):
                if not inspect.getargspec(thing)[0]:
                    ret = _any(thing())
            else:
                ret = smart_unicode(thing, strings_only=True)

            return ret

        def _fk(data, field):
            """
            Foreign keys.
            """
            return _any(getattr(data, field.name))
        
        def _related(data, fields=()):
            """
            Foreign keys.
            """
            return [ _model(m, fields) for m in data.iterator() ]
        
        def _m2m(data, field, fields=()):
            """
            Many to many (re-route to `_model`.)
            """
            return [ _model(m, fields) for m in getattr(data, field.name).iterator() ]
        
        def _model(data, fields=()):
            """
            Models. Will respect the `fields` and/or
            `exclude` on the handler (see `typemapper`.)
            """
            ret = { }
            
            if self.in_typemapper(type(data), self.anonymous) or fields:

                v = lambda f: getattr(data, f.attname)

                if not fields:
                    """
                    Fields was not specified, try to find teh correct
                    version in the typemapper we were sent.
                    """
                    mapped = self.in_typemapper(type(data), self.anonymous)
                    get_fields = set(mapped.fields)
                    exclude_fields = set(mapped.exclude).difference(get_fields)
                
                    if not get_fields:
                        get_fields = set([ f.attname.replace("_id", "", 1)
                            for f in data._meta.fields ])
                
                    # sets can be negated.
                    for exclude in exclude_fields:
                        if isinstance(exclude, basestring):
                            get_fields.discard(exclude)
                        elif isinstance(exclude, re._pattern_type):
                            for field in get_fields.copy():
                                if exclude.match(field):
                                    get_fields.discard(field)
                                    
                else:
                    get_fields = set(fields)

                for f in data._meta.local_fields:
                    if f.serialize:
                        if not f.rel:
                            if f.attname in get_fields:
                                ret[f.attname] = _any(v(f))
                                get_fields.remove(f.attname)
                        else:
                            if f.attname[:-3] in get_fields:
                                ret[f.name] = _fk(data, f)
                                get_fields.remove(f.name)
                
                for mf in data._meta.many_to_many:
                    if mf.serialize:
                        if mf.attname in get_fields:
                            ret[mf.name] = _m2m(data, mf)
                            get_fields.remove(mf.name)
                
                # try to get the remainder of fields
                for maybe_field in get_fields:

                    if isinstance(maybe_field, (list, tuple)):
                        model, fields = maybe_field
                        inst = getattr(data, model, None)

                        if inst:
                            if hasattr(inst, 'all'):
                                ret[model] = _related(inst, fields)
                            else:
                                ret[model] = _model(inst, fields)

                    else:                    
                        maybe = getattr(data, maybe_field, None)
                        if maybe:
                            if isinstance(maybe, (int, basestring)):
                                ret[maybe_field] = _any(maybe)
                        else:
                            handler_f = getattr(self.handler, maybe_field, None)

                            if handler_f:
                                ret[maybe_field] = handler_f(data)

            else:
                for f in data._meta.fields:
                    ret[f.attname] = _any(getattr(data, f.attname))
                
                fields = dir(data.__class__) + ret.keys()
                add_ons = [k for k in dir(data) if k not in fields]
                
                for k in add_ons:
                    ret[k] = _any(getattr(data, k))
            
            # resouce uri
            if self.in_typemapper(type(data), self.anonymous):
                handler = self.in_typemapper(type(data), self.anonymous)
                if hasattr(handler, 'resource_uri'):
                    url_id, fields = handler.resource_uri()
                    ret['resource_uri'] = permalink( lambda: (url_id, 
                        (getattr(data, f) for f in fields) ) )()
            
            if hasattr(data, 'get_api_url') and 'resource_uri' not in ret:
                try: ret['resource_uri'] = data.get_api_url()
                except: pass
            
            # absolute uri
            if hasattr(data, 'get_absolute_url'):
                try: ret['absolute_uri'] = data.get_absolute_url()
                except: pass
            
            return ret
        
        def _list(data):
            """
            Lists.
            """
            return [ _any(v) for v in data ]
            
        def _dict(data):
            """
            Dictionaries.
            """
            return dict([ (k, _any(v)) for k, v in data.iteritems() ])
            
        # Kickstart the seralizin'.
        return _any(self.data, self.fields)
    
    def in_typemapper(self, model, anonymous):
        for klass, (km, is_anon) in self.typemapper.iteritems():
            if model is km and is_anon is anonymous:
                return klass
        
    def render(self):
        """
        This super emitter does not implement `render`,
        this is a job for the specific emitter below.
        """
        raise NotImplementedError("Please implement render.")
        
    @classmethod
    def get(cls, format):
        """
        Gets an emitter, returns the class and a content-type.
        """
        if cls.EMITTERS.has_key(format):
            return cls.EMITTERS.get(format)

        raise ValueError("No emitters found for type %s" % format)
    
    @classmethod
    def register(cls, name, klass, content_type='text/plain'):
        """
        Register an emitter.
        
        Parameters::
         - `name`: The name of the emitter ('json', 'xml', 'yaml', ...)
         - `klass`: The emitter class.
         - `content_type`: The content type to serve response as.
        """
        cls.EMITTERS[name] = (klass, content_type)
        
    @classmethod
    def unregister(cls, name):
        """
        Remove an emitter from the registry. Useful if you don't
        want to provide output in one of the built-in emitters.
        """
        return cls.EMITTERS.pop(name, None)
    
class XMLEmitter(Emitter):
    def _to_xml(self, xml, data):
        if isinstance(data, (list, tuple)):
            for item in data:
                xml.startElement("resource", {})
                self._to_xml(xml, item)
                xml.endElement("resource")
        elif isinstance(data, dict):
            for key, value in data.iteritems():
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)
        else:
            xml.characters(smart_unicode(data))

    def render(self, request):
        stream = StringIO.StringIO()
        
        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("response", {})
        
        self._to_xml(xml, self.construct())
        
        xml.endElement("response")
        xml.endDocument()
        
        return stream.getvalue()

Emitter.register('xml', XMLEmitter, 'text/xml; charset=utf-8')
Mimer.register(lambda *a: None, ('text/xml',))

class JSONEmitter(Emitter):
    """
    JSON emitter, understands timestamps.
    """
    def render(self, request):
        cb = request.GET.get('callback')
        seria = simplejson.dumps(self.construct(), cls=DateTimeAwareJSONEncoder)

        # Callback
        if cb:
            return '%s(%s)' % (cb, seria)

        return seria
    
Emitter.register('json', JSONEmitter, 'application/json; charset=utf-8')
Mimer.register(simplejson.loads, ('application/json',))
    
class YAMLEmitter(Emitter):
    """
    YAML emitter, uses `safe_dump` to omit the
    specific types when outputting to non-Python.
    """
    def render(self, request):
        return yaml.safe_dump(self.construct())

if yaml:  # Only register yaml if it was import successfully.
    Emitter.register('yaml', YAMLEmitter, 'application/x-yaml; charset=utf-8')
    Mimer.register(yaml.load, ('application/x-yaml',))

class PickleEmitter(Emitter):
    """
    Emitter that returns Python pickled.
    """
    def render(self, request):
        return pickle.dumps(self.construct())
        
Emitter.register('pickle', PickleEmitter, 'application/python-pickle')
Mimer.register(pickle.loads, ('application/python-pickle',))
