import types, decimal, yaml, copy
from django.db.models.query import QuerySet
from django.db.models import Model, permalink
from django.utils import simplejson
from django.utils.xmlutils import SimplerXMLGenerator
from django.utils.encoding import smart_unicode
from django.core.serializers.json import DateTimeAwareJSONEncoder

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class Emitter(object):
    def __init__(self, payload, typemapper):
        self.typemapper = typemapper
        self.data = payload
    
        if isinstance(self.data, Exception):
            raise
    
    def construct(self):
        
        def _any(thing):

            ret = None
            
            if isinstance(thing, (tuple, list, QuerySet)):
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

        def _fk(data, field):
            return _any(getattr(data, field.name))
            
        def _m2m(data, field):
            return [ _model(m) for m in getattr(data, field.name).iterator() ]

        def _model(data):
            ret = { }
            
            if type(data) in self.typemapper.keys():

                v = lambda f: getattr(data, f.attname)
                want_fields = copy.copy(list(self.typemapper.get(type(data)).fields))
                
                for f in data._meta.local_fields:
                    if f.serialize:
                        if not f.rel:
                            if f.attname in want_fields:
                                ret[f.attname] = _any(v(f))
                                want_fields.remove(f.attname)
                        else:
                            if f.attname[:-3] in want_fields:
                                ret[f.name] = _fk(data, f)
                                want_fields.remove(f.name)

                for mf in data._meta.many_to_many:
                    if mf.serialize:
                        if mf.attname in want_fields:
                            ret[mf.name] = _m2m(data, mf)
                            want_fields.remove(mf.name)
                            
                # try to get the remainder of fields
                for maybe_field in want_fields:
                    maybe = getattr(data, maybe_field, None)

                    if maybe:
                        if isinstance(maybe, (int, basestring)):
                            ret[maybe_field] = _any(maybe)
                            
            else:

                for f in data._meta.fields:
                    ret[f.attname] = _any(getattr(data, f.attname))

                fields = dir(data.__class__) + ret.keys()
                add_ons = [k for k in dir(data) if k not in fields]
            
                for k in add_ons:
                    ret[k] = _any(getattr(data, k))
            
            # resouce uri
            if type(data) in self.typemapper.keys():
                handler = self.typemapper.get(type(data))
                if hasattr(handler, 'resource_uri'):
                    url_id, fields = handler.resource_uri()
                    ret['resource_uri'] = permalink( lambda: (url_id, 
                        (getattr(data, f) for f in fields) ) )()
            elif hasattr(data, 'get_api_url'):
                try: ret['resource_uri'] = data.get_api_url()
                except: pass
            
            return ret
            
        def _list(data):
            return [ _any(v) for v in data ]
            
        def _dict(data):
            return dict([ (k, _any(v)) for k, v in data.iteritems() ])
            
        return _any(self.data)
    
    def render(self):
        raise NotImplementedError("Please implement render.")
        
    @classmethod
    def get(cls, format):
        if format == 'xml':
            return XMLEmitter, 'text/plain; charset=utf-8'
        elif format == 'json':
            return JSONEmitter, 'text/plain; charset=utf-8'
        elif format == 'yaml':
            return YAMLEmitter, 'text/plain; charset=utf-8'
    
class XMLEmitter(Emitter):
    def _to_xml(self, xml, data):
        if isinstance(data, (list, tuple)):
            for item in data:
                self._to_xml(xml, item)
        elif isinstance(data, dict):
            for key, value in data.iteritems():
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)
        elif data:
            xml.characters(smart_unicode(data))

    def render(self):
        stream = StringIO.StringIO()
        
        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("response", {})
        
        self._to_xml(xml, self.construct())
        
        xml.endElement("response")
        xml.endDocument()
        
        return stream.getvalue()

class JSONEmitter(Emitter):
    # TODO: callback functions
    def render(self):
        return simplejson.dumps(self.construct(), cls=DateTimeAwareJSONEncoder)
    
class YAMLEmitter(Emitter):
    def render(self):
        return yaml.safe_dump(self.construct())
