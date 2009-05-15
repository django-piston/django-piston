from piston.handler import BaseHandler, AnonymousBaseHandler
from piston.utils import rc, require_mime, require_extended

from blogserver.blog.models import Blogpost

class AnonymousBlogpostHandler(AnonymousBaseHandler):
    model = Blogpost
    fields = ('id', 'title', 'content', 'created_on')

class BlogpostHandler(BaseHandler):
    model = Blogpost
    anonymous = AnonymousBlogpostHandler
    fields = ('title', 'content', ('author', ('username',)), 
              'created_on', 'content_length')
    
    def content_length(self, blogpost):
        return len(blogpost.content)
        
    @require_extended
    def create(self, request):
        attrs = self.flatten_dict(request.POST)

        if self.exists(**attrs):
            return rc.DUPLICATE_ENTRY
        else:
            post = Blogpost(title=attrs['title'], 
                            content=attrs['content'],
                            author=request.user)
            post.save()
            
            return post
        