from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import HttpBasicAuthentication

from test_project.apps.testapp.handlers import EntryHandler, ExpressiveHandler

auth = HttpBasicAuthentication(realm='TestApplication')

entries = Resource(handler=EntryHandler, authentication=auth)
expressive = Resource(handler=ExpressiveHandler, authentication=auth)

urlpatterns = patterns('',
    url(r'^entries/$', entries),
    url(r'^entries/(?P<pk>.+)/$', entries),
    url(r'^entries\.(?P<emitter_format>.+)', entries),
    url(r'^entry-(?P<pk>.+)\.(?P<emitter_format>.+)', entries),
    
    url(r'^expressive\.(?P<emitter_format>.+)$', expressive),
)


