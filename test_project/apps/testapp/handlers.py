from django.core.paginator import Paginator

from piston.handler import BaseHandler
from piston.utils import rc, validate

from .models import TestModel

class EntryHandler(BaseHandler):
    model = TestModel
    allowed_methods = ['GET']

    def read(self, request, pk=None):
        if pk is not None:
            return TestModel.objects.get(pk=int(pk))
        paginator = Paginator(TestModel.objects.all(), 25)
        return paginator.page(int(request.GET.get('page', 1))).object_list

