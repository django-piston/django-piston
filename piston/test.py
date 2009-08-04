# Django imports
import django.test.client as client
import django.test as test

# Piston imports
from piston import oauth

class OAuthClient(oauth.OAuthClient):
    def __init__(self, consumer, token):
        self.token = oauth.OAuthToken(token.key, token.secret)
        self.consumer = oauth.OAuthConsumer(consumer.key, consumer.secret)
        self.signature = oauth.OAuthSignatureMethod_HMAC_SHA1()

    def get(self, path, data={}, headers={}):
        pass

    def post(self, path, data={}, headers={}, content_type=client.MULTIPART_CONTENT):
        pass

    def request(self, path, data={}, headers={}):
        pass

class TestCase(test.TestCase):
    pass

class OAuthTestCase(TestCase):
    fixtures = ['oauth.json']

