from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import HttpBasicAuthentication

from test_project.apps.testapp.handlers import EntryHandler, ExpressiveHandler, AbstractHandler, EchoHandler, PlainOldObjectHandler

auth = HttpBasicAuthentication(realm='TestApplication')

entries = Resource(handler=EntryHandler, authentication=auth)
expressive = Resource(handler=ExpressiveHandler, authentication=auth)
abstract = Resource(handler=AbstractHandler, authentication=auth)
echo = Resource(handler=EchoHandler)
popo = Resource(handler=PlainOldObjectHandler)


urlpatterns = patterns('',
    url(r'^entries/$', entries),
    url(r'^entries/(?P<pk>.+)/$', entries),
    url(r'^entries\.(?P<emitter_format>.+)', entries),
    url(r'^entry-(?P<pk>.+)\.(?P<emitter_format>.+)', entries),

    url(r'^expressive\.(?P<emitter_format>.+)$', expressive),

    url(r'^abstract\.(?P<emitter_format>.+)$', abstract),
    url(r'^abstract/(?P<id_>\d+)\.(?P<emitter_format>.+)$', abstract),

    url(r'^echo$', echo),

    # oauth entrypoints
    url(r'^oauth/request_token$', 'piston.authentication.oauth_request_token'),
    url(r'^oauth/authorize$', 'piston.authentication.oauth_user_auth'),
    url(r'^oauth/access_token$', 'piston.authentication.oauth_access_token'),
    
    url(r'^popo$', popo),
)


