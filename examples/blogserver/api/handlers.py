from piston.handler import BaseHandler, AnonymousBaseHandler

from blogserver.blog.models import Blogpost

class AnonymousBlogpostHandler(AnonymousBaseHandler):
    model = Blogpost
    fields = ('title', 'content', 'created_on')

class BlogpostHandler(BaseHandler):
    model = Blogpost
    anonymous = AnonymousBlogpostHandler
    fields = ('title', 'content', ('author', ('username',)), 
              'created_on', 'content_length')
    
    def content_length(self, blogpost):
        return len(blogpost.content)