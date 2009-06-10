from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import simplejson
from django.conf import settings

from piston import oauth
from piston.models import Consumer, Token
from piston.forms import OAuthAuthenticationForm

try:
    import yaml
except ImportError:
    print "Can't run YAML testsuite"
    yaml = None

import urllib, base64

from test_project.apps.testapp.models import TestModel, ExpressiveTestModel, Comment, InheritedModel
from test_project.apps.testapp import signals

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



class OAuthTests(MainTests):
    signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

    def setUp(self):
        super(OAuthTests, self).setUp()

        self.consumer = Consumer(name='Test Consumer', description='Test', status='accepted')
        self.consumer.generate_random_codes()
        self.consumer.save()

    def tearDown(self):
        super(OAuthTests, self).tearDown()
        self.consumer.delete()

    def test_handshake(self):
        '''Test the OAuth handshake procedure
        '''
        oaconsumer = oauth.OAuthConsumer(self.consumer.key, self.consumer.secret)

        # Get a request key...
        request = oauth.OAuthRequest.from_consumer_and_token(oaconsumer,
                http_url='http://testserver/api/oauth/request_token')
        request.sign_request(self.signature_method, oaconsumer, None)

        response = self.client.get('/api/oauth/request_token', request.parameters)
        oatoken = oauth.OAuthToken.from_string(response.content)

        token = Token.objects.get(key=oatoken.key, token_type=Token.REQUEST)
        self.assertEqual(token.secret, oatoken.secret)

        # Simulate user authentication...
        self.failUnless(self.client.login(username='admin', password='admin'))
        request = oauth.OAuthRequest.from_token_and_callback(token=oatoken,
                callback='http://printer.example.com/request_token_ready',
                http_url='http://testserver/api/oauth/authorize')
        request.sign_request(self.signature_method, oaconsumer, oatoken)

        # Request the login page
# TODO: Parse the response to make sure all the fields exist
#        response = self.client.get('/api/oauth/authorize', {
#            'oauth_token': oatoken.key,
#            'oauth_callback': 'http://printer.example.com/request_token_ready',
#            })

        response = self.client.post('/api/oauth/authorize', {
            'oauth_token': oatoken.key,
            'oauth_callback': 'http://printer.example.com/request_token_ready',
            'csrf_signature': OAuthAuthenticationForm.get_csrf_signature(settings.SECRET_KEY, oatoken.key),
            'authorize_access': 1,
            })

        # Response should be a redirect...
        self.assertEqual(302, response.status_code)
        self.assertEqual('http://printer.example.com/request_token_ready?oauth_token='+oatoken.key, response['Location'])

        # Obtain access token...
        request = oauth.OAuthRequest.from_consumer_and_token(oaconsumer, token=oatoken,
                http_url='http://testserver/api/oauth/access_token')
        request.sign_request(self.signature_method, oaconsumer, oatoken)
        response = self.client.get('/api/oauth/access_token', request.parameters)

        oa_atoken = oauth.OAuthToken.from_string(response.content)
        atoken = Token.objects.get(key=oa_atoken.key, token_type=Token.ACCESS)
        self.assertEqual(atoken.secret, oa_atoken.secret)

 
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

class AbstractBaseClassTests(MainTests):
    def init_delegate(self):
        self.ab1 = InheritedModel()
        self.ab1.save()
        self.ab2 = InheritedModel()
        self.ab2.save()
        
    def test_field_presence(self):
        result = self.client.get('/api/abstract.json',
                HTTP_AUTHORIZATION=self.auth_string).content
                
        expected = """[
    {
        "id": 1, 
        "some_other": "something else", 
        "some_field": "something here"
    }, 
    {
        "id": 2, 
        "some_other": "something else", 
        "some_field": "something here"
    }
]"""
        
        self.assertEquals(result, expected)

    def test_specific_id(self):
        ids = (1, 2)
        be = """{
    "id": %d, 
    "some_other": "something else", 
    "some_field": "something here"
}"""
        
        for id_ in ids:
            result = self.client.get('/api/abstract/%d.json' % id_,
                    HTTP_AUTHORIZATION=self.auth_string).content
                    
            expected = be % id_
            
            self.assertEquals(result, expected)

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
    
        expected = """[
    {
        "content": "bar", 
        "comments": [], 
        "title": "foo"
    }, 
    {
        "content": "bar2", 
        "comments": [], 
        "title": "foo2"
    }
]"""
    
        result = self.client.get('/api/expressive.json',
            HTTP_AUTHORIZATION=self.auth_string).content

        self.assertEquals(result, expected)
        
        resp = self.client.post('/api/expressive.json', outgoing, content_type='application/json',
            HTTP_AUTHORIZATION=self.auth_string)
            
        self.assertEquals(resp.status_code, 201)
        
        expected = """[
    {
        "content": "bar", 
        "comments": [], 
        "title": "foo"
    }, 
    {
        "content": "bar2", 
        "comments": [], 
        "title": "foo2"
    }, 
    {
        "content": "test", 
        "comments": [
            {
                "content": "test1"
            }, 
            {
                "content": "test2"
            }
        ], 
        "title": "test"
    }
]"""
        
        result = self.client.get('/api/expressive.json', 
            HTTP_AUTHORIZATION=self.auth_string).content
            
        self.assertEquals(result, expected)

    def test_incoming_invalid_json(self):
        resp = self.client.post('/api/expressive.json',
            'foo',
            HTTP_AUTHORIZATION=self.auth_string,
            content_type='application/json')
        self.assertEquals(resp.status_code, 400)

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

    def test_incoming_invalid_yaml(self):
        resp = self.client.post('/api/expressive.yaml',
            '  8**sad asj lja foo',
            HTTP_AUTHORIZATION=self.auth_string,
            content_type='application/yaml')
        self.assertEquals(resp.status_code, 400)

class Issue36RegressionTests(MainTests):
    """
    This testcase addresses #36 in django-piston where request.FILES is passed
    empty to the handler if the request.method is PUT.
    """
    def fetch_request(self, sender, request, *args, **kwargs):
        self.request = request

    def setUp(self):
        super(self.__class__, self).setUp()
        self.data = TestModel()
        self.data.save()
        # Register to the WSGIRequest signals to get the latest generated
        # request object.
        signals.entry_request_started.connect(self.fetch_request)

    def tearDown(self):
        super(self.__class__, self).tearDown()
        self.data.delete()
        signals.entry_request_started.disconnect(self.fetch_request)
    
    def test_simple(self):
        # First try it with POST to see if it works there
        if True:
            fp = open(__file__, 'r')
            try:
                response = self.client.post('/api/entries.xml',
                        {'file':fp}, HTTP_AUTHORIZATION=self.auth_string)
                self.assertEquals(1, len(self.request.FILES), 'request.FILES on POST is empty when it should contain 1 file')
            finally:
                fp.close()

        if not hasattr(self.client, 'put'):
            import warnings
            warnings.warn('Issue36RegressionTest partially requires Django 1.1 or newer. Skipped.')
            return

        # ... and then with PUT
        fp = open(__file__, 'r')
        try:
            response = self.client.put('/api/entry-%d.xml' % self.data.pk,
                    {'file': fp}, HTTP_AUTHORIZATION=self.auth_string)
            self.assertEquals(1, len(self.request.FILES), 'request.FILES on PUT is empty when it should contain 1 file')
        finally:
            fp.close()

class ValidationTest(MainTests):
    def test_basic_validation_fails(self):
        resp = self.client.get('/api/echo')
        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.content, 'Bad Request: <ul class="errorlist">'
            '<li>msg<ul class="errorlist"><li>This field is required.</li>'
            '</ul></li></ul>')

    def test_basic_validation_succeeds(self):
        data = {'msg': 'donuts!'}
        resp = self.client.get('/api/echo', data)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(data, simplejson.loads(resp.content))

class PlainOldObject(MainTests):
    def test_plain_object_serialization(self):
        resp = self.client.get('/api/popo')
        self.assertEquals(resp.status_code, 200)
        self.assertEquals({'type': 'plain', 'field': 'a field'}, simplejson.loads(resp.content))
        