# Django imports
from django.core import mail
from django.contrib.auth.models import User
from django.conf import settings
from django.http import HttpRequest
from django.utils import simplejson

# Piston imports
from test import TestCase
from models import Consumer
from handler import BaseHandler
from utils import rc
from resource import Resource

class ConsumerTest(TestCase):
    fixtures = ['models.json']

    def setUp(self):
        self.consumer = Consumer()
        self.consumer.name = "Piston Test Consumer"
        self.consumer.description = "A test consumer for Piston."
        self.consumer.user = User.objects.get(pk=3)
        self.consumer.generate_random_codes()

    def test_create_pending(self):
        """ Ensure creating a pending Consumer sends proper emails """
        # If it's pending we should have two messages in the outbox; one 
        # to the consumer and one to the site admins.
        if len(settings.ADMINS):
            self.assertEquals(len(mail.outbox), 2)
        else:
            self.assertEquals(len(mail.outbox), 1)

        expected = "Your API Consumer for example.com is awaiting approval."
        self.assertEquals(mail.outbox[0].subject, expected)

    def test_delete_consumer(self):
        """ Ensure deleting a Consumer sends a cancel email """

        # Clear out the outbox before we test for the cancel email.
        mail.outbox = []

        # Delete the consumer, which should fire off the cancel email.
        self.consumer.delete() 
        
        self.assertEquals(len(mail.outbox), 1)
        expected = "Your API Consumer for example.com has been canceled."
        self.assertEquals(mail.outbox[0].subject, expected)


class CustomResponseWithStatusCodeTest(TestCase):
     """
     Test returning content to be formatted and a custom response code from a 
     handler method. In this case we're returning 201 (created) and a dictionary 
     of data. This data will be formatted as json. 
     """

     def test_reponse_with_data_and_status_code(self):
         response_data = dict(complex_response=dict(something='good', 
             something_else='great'))

         class MyHandler(BaseHandler):
             """
             Handler which returns a response w/ both data and a status code (201)
             """
             allowed_methods = ('POST', )

             def create(self, request):
                 resp = rc.CREATED
                 resp.content = response_data
                 return resp

         resource = Resource(MyHandler)
         request = HttpRequest()
         request.method = 'POST'
         response = resource(request, emitter_format='json')

         self.assertEquals(201, response.status_code)
         self.assertTrue(response._is_string, "Expected response content to be a string")

         # compare the original data dict with the json response 
         # converted to a dict
         self.assertEquals(response_data, simplejson.loads(response.content))
