from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import simplejson

try:
    import yaml
except ImportError:
    print "Can't run YAML testsuite"
    yaml = None

import base64

from test_project.apps.testapp.models import TestModel, ExpressiveTestModel, Comment

class MainTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('admin', 'admin@world.com', 'admin')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.is_active = True
        self.user.save()
        self.auth_string = 'Basic %s' % base64.encodestring('admin:admin').rstrip()

        if hasattr(self, 'init_delegate'):
            self.init_delegate()
        
    def tearDown(self):
        self.user.delete()
 
class MultiXMLTests(MainTests):
    def init_delegate(self):
        self.t1_data = TestModel()
        self.t1_data.save()
        self.t2_data = TestModel()
        self.t2_data.save()

    def test_multixml(self):
        expected = '<?xml version="1.0" encoding="utf-8"?>\n<response><resource><test1>None</test1><test2>None</test2></resource><resource><test1>None</test1><test2>None</test2></resource></response>'
        result = self.client.get('/api/entries.xml',
                HTTP_AUTHORIZATION=self.auth_string).content
        self.assertEquals(expected, result)

    def test_singlexml(self):
        obj = TestModel.objects.all()[0]
        expected = '<?xml version="1.0" encoding="utf-8"?>\n<response><test1>None</test1><test2>None</test2></response>'
        result = self.client.get('/api/entry-%d.xml' % (obj.pk,),
                HTTP_AUTHORIZATION=self.auth_string).content
        self.assertEquals(expected, result)

class IncomingExpressiveTests(MainTests):
    def init_delegate(self):
        e1 = ExpressiveTestModel(title="foo", content="bar")
        e1.save()
        e2 = ExpressiveTestModel(title="foo2", content="bar2")
        e2.save()

    def test_incoming_json(self):
        outgoing = simplejson.dumps({ 'title': 'test', 'content': 'test',
                                      'comments': [ { 'content': 'test1' },
                                                    { 'content': 'test2' } ] })
    
        expected = '[{"content": "bar", "comments": [], "title": "foo"}, {"content": "bar2", "comments": [], "title": "foo2"}]'
    
        self.assertEquals(self.client.get('/api/expressive.json', 
            HTTP_AUTHORIZATION=self.auth_string).content, expected)
        
        resp = self.client.post('/api/expressive.json', outgoing, content_type='application/json',
            HTTP_AUTHORIZATION=self.auth_string)
            
        self.assertEquals(resp.status_code, 201)
        
        expected = '[{"content": "bar", "comments": [], "title": "foo"}, {"content": "bar2", "comments": [], "title": "foo2"}, {"content": "test", "comments": [{"content": "test1"}, {"content": "test2"}], "title": "test"}]'
        
        self.assertEquals(self.client.get('/api/expressive.json', 
            HTTP_AUTHORIZATION=self.auth_string).content, expected)
        
    def test_incoming_yaml(self):
        if not yaml:
            return
            
        expected = """- comments: []
  content: bar
  title: foo
- comments: []
  content: bar2
  title: foo2
"""
          
        self.assertEquals(self.client.get('/api/expressive.yaml',
            HTTP_AUTHORIZATION=self.auth_string).content, expected)

        outgoing = yaml.dump({ 'title': 'test', 'content': 'test',
                                      'comments': [ { 'content': 'test1' },
                                                    { 'content': 'test2' } ] })
            
        resp = self.client.post('/api/expressive.json', outgoing, content_type='application/x-yaml',
            HTTP_AUTHORIZATION=self.auth_string)
        
        self.assertEquals(resp.status_code, 201)
        
        expected = """- comments: []
  content: bar
  title: foo
- comments: []
  content: bar2
  title: foo2
- comments:
  - {content: test1}
  - {content: test2}
  content: test
  title: test
"""
        self.assertEquals(self.client.get('/api/expressive.yaml', 
            HTTP_AUTHORIZATION=self.auth_string).content, expected)