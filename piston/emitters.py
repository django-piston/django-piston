import types, decimal, yaml
from django.db.models.query import QuerySet
from django.db.models import Model
from django.utils import simplejson
from django.core.serializers.json import DateTimeAwareJSONEncoder

class Emitter(object):
    def __init__(self, payload, fields=()):
        if isinstance(payload, QuerySet):
            self.data = tuple([m for m in payload.all()])
        elif isinstance(payload, Model):
            self.data = (payload,)
        else:
            raise ValueError("Can't emit this.")
    
    def construct(self):
        
        def _any(thing):
            ret = None
            
            if isinstance(thing, (tuple, list)):
                ret = _list(thing)
            elif isinstance(thing, dict):
                ret = _dict(thing)
            elif isinstance(thing, decimal.Decimal):
                ret = str(thing)
            elif isinstance(thing, Model):
                ret = _model(thing)
            elif isinstance(thing, unicode):
                ret = thing.encode('utf-8')
            else:
                ret = thing

            return ret

        def _model(data):
            ret = { }
            
            for f in data._meta.fields:
                ret[f.attname] = _any(getattr(data, f.attname))
            
            fields = dir(data.__class__) + ret.keys()
            add_ons = [k for k in dir(data) if k not in fields]
            
            for k in add_ons:
                ret[k] = _any(getattr(data, k))
                
            return ret
            
        def _list(data):
            return [ _any(v) for v in data ]
            
        def _dict(data):
            ret = { }
            
            for k, v in data.iteritems():
                ret[k] = _any(v)
                
            return ret
            
        return _any(self.data)
    
    def render(self):
        raise NotImplementedError("Please implement render.")
        
    @classmethod
    def get(cls, format):
        if format == 'xml':
            return XMLEmitter, 'text/plain'
        elif format == 'json':
            return JSONEmitter, 'text/plain'
        elif format == 'yaml':
            return YAMLEmitter, 'text/plain'
    
class XMLEmitter(Emitter):
    pass
    
class JSONEmitter(Emitter):
    def render(self):
        return simplejson.dumps(self.construct(), cls=DateTimeAwareJSONEncoder)
    
class YAMLEmitter(Emitter):
    def render(self):
        return yaml.dump(self.construct())
