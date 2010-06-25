# Django imports
from django.core import mail
from django.contrib.auth.models import User
from django.conf import settings
from django.template import loader, TemplateDoesNotExist
from django.http import HttpRequest, HttpResponse
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

    def _pre_test_email(self):
        template = "piston/mails/consumer_%s.txt" % self.consumer.status
        try:
            loader.render_to_string(template, {
                'consumer': self.consumer,
                'user': self.consumer.user
            })
            return True
        except TemplateDoesNotExist:
            """
            They haven't set up the templates, which means they might not want
            these emails sent.
            """
            return False

    def test_create_pending(self):
        """ Ensure creating a pending Consumer sends proper emails """
        # Verify if the emails can be sent
        if not self._pre_test_email():
            return

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

        # Verify if the emails can be sent
        if not self._pre_test_email():
            return

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


class ErrorHandlerTest(TestCase):
    def test_customized_error_handler(self):
        """
        Throw a custom error from a handler method and catch (and format) it 
        in an overridden error_handler method on the associated Resource object
        """
        class GoAwayError(Exception):
            def __init__(self, name, reason):
                self.name = name
                self.reason = reason

        class MyHandler(BaseHandler):
            """
            Handler which raises a custom exception 
            """
            allowed_methods = ('GET',)

            def read(self, request):
                raise GoAwayError('Jerome', 'No one likes you')

        class MyResource(Resource):
            def error_handler(self, error, request, meth, em_format):
                # if the exception is our exeption then generate a 
                # custom response with embedded content that will be 
                # formatted as json 
                if isinstance(error, GoAwayError):
                    response = rc.FORBIDDEN
                    response.content = dict(error=dict(
                        name=error.name, 
                        message="Get out of here and dont come back", 
                        reason=error.reason
                    ))    

                    return response

                return super(MyResource, self).error_handler(error, request, meth)

        resource = MyResource(MyHandler)

        request = HttpRequest()
        request.method = 'GET'
        response = resource(request, emitter_format='json')

        self.assertEquals(401, response.status_code)

        # verify the content we got back can be converted back to json 
        # and examine the dictionary keys all exist as expected
        response_data = simplejson.loads(response.content)
        self.assertTrue('error' in response_data)
        self.assertTrue('name' in response_data['error'])
        self.assertTrue('message' in response_data['error'])
        self.assertTrue('reason' in response_data['error'])

    def test_type_error(self):
        """
        Verify that type errors thrown from a handler method result in a valid 
        HttpResonse object being returned from the error_handler method
        """
        class MyHandler(BaseHandler):
            def read(self, request):
                raise TypeError()

        request = HttpRequest()
        request.method = 'GET'
        response = Resource(MyHandler)(request)

        self.assertTrue(isinstance(response, HttpResponse), "Expected a response, not: %s" 
            % response)


    def test_other_error(self):
        """
        Verify that other exceptions thrown from a handler method result in a valid
        HttpResponse object being returned from the error_handler method
        """
        class MyHandler(BaseHandler):
            def read(self, request):
                raise Exception()

        resource = Resource(MyHandler)
        resource.display_errors = True
        resource.email_errors = False

        request = HttpRequest()
        request.method = 'GET'
        response = resource(request)

        self.assertTrue(isinstance(response, HttpResponse), "Expected a response, not: %s" 
            % response)
