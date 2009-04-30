from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import HttpBasicAuthentication

from blogserver.api.handlers import BlogpostHandler

auth = HttpBasicAuthentication(realm='My sample API')

blogposts = Resource(handler=BlogpostHandler, authentication=auth)

urlpatterns = patterns('',
    url(r'^posts/$', blogposts),
    url(r'^posts/(?P<emitter_format>.+)/$', blogposts),
    url(r'^posts\.(?P<emitter_format>.+)', blogposts),
)