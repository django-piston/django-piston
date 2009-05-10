from django.core.paginator import Paginator

from piston.handler import BaseHandler
from piston.utils import rc, validate

from models import TestModel, ExpressiveTestModel, Comment

class EntryHandler(BaseHandler):
    model = TestModel
    allowed_methods = ['GET']

    def read(self, request, pk=None):
        if pk is not None:
            return TestModel.objects.get(pk=int(pk))
        paginator = Paginator(TestModel.objects.all(), 25)
        return paginator.page(int(request.GET.get('page', 1))).object_list

class ExpressiveHandler(BaseHandler):
    model = ExpressiveTestModel
    fields = ('title', 'content', ('comments', ('content',)))

    @classmethod
    def comments(cls, em):
        return em.comments.all()

    def read(self, request):
        inst = ExpressiveTestModel.objects.all()
        
        return inst
        
    def create(self, request):
        if request.content_type:
            data = request.data
            
            em = self.model(title=data['title'], content=data['content'])
            em.save()
            
            for comment in data['comments']:
                Comment(parent=em, content=comment['content']).save()
                
            return rc.CREATED
        else:
            super(ExpressiveTestModel, self).create(request)
            