from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.template import loader
from django.conf import settings

import oauth
from store import DataStore

def django_auth(username, password):
    """
    Basic callback for `HttpBasicAuthentication`
    which checks the username and password up
    against Djangos built-in authentication system.
    
    On success, returns the `User`, *not* boolean!
    """
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return user
        else:
            return False
    except User.DoesNotExist:
        return False

class HttpBasicAuthentication(object):
    """
    Basic HTTP authenticater. Synopsis:
    
    Authentication handlers must implement two methods:
     - `is_authenticated`: Will be called when checking for
        authentication. Receives a `request` object, please
        set your `User` object on `request.user`, otherwise
        return False (or something that evaluates to False.)
     - `challenge`: In cases where `is_authenticated` returns
        False, the result of this method will be returned.
        This will usually be a `HttpResponse` object with
        some kind of challenge headers and 401 code on it.
    """
    def __init__(self, auth_func=django_auth, realm='Bitbucket.org API'):
        self.auth_func = auth_func
        self.realm = realm

    def is_authenticated(self, request):
        auth_string = request.META.get('HTTP_AUTHORIZATION', None)

        if not auth_string:
            return False
            
        (authmeth, auth) = auth_string.split(" ", 1)
        
        if not authmeth.lower() == 'basic':
            return False
            
        auth = auth.strip().decode('base64')
        (username, password) = auth.split(':', 1)
        
        request.user = self.auth_func(username, password)
        
        return not request.user is False
        
    def challenge(self):
        resp = HttpResponse("Authorization Required")
        resp['WWW-Authenticate'] = 'Basic realm="%s"' % self.realm
        resp.status_code = 401
        return resp

def initialize_server_request(request):
    """Shortcut for initialization."""
    oauth_request = oauth.OAuthRequest.from_request(
        request.method, request.build_absolute_uri(), 
        headers=request.META, parameters=dict(request.REQUEST.items()),
        query_string=request.environ.get('QUERY_STRING', ''))
        
    if oauth_request:
        oauth_server = oauth.OAuthServer(DataStore(oauth_request))
        oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
        oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())
    else:
        oauth_server = None
        
    return oauth_server, oauth_request

def send_oauth_error(err=None):
    """Shortcut for sending an error."""
    # send a 401 error
    response = HttpResponse(err.message.encode('utf-8'))
    response.status_code = 401
    # return the authenticate header
    realm = 'Bitbucket.org OAuth'
    header = oauth.build_authenticate_header(realm=realm)
    for k, v in header.iteritems():
        response[k] = v
    return response

def oauth_request_token(request):
    oauth_server, oauth_request = initialize_server_request(request)
    
    if oauth_server is None:
        return INVALID_PARAMS_RESPONSE
    try:
        # create a request token
        token = oauth_server.fetch_request_token(oauth_request)
        # return the token
        response = HttpResponse(token.to_string())
    except oauth.OAuthError, err:
        response = send_oauth_error(err)
    return response

def oauth_auth_view(request, token, callback, params):
    return HttpResponse("Just a fake view for auth.")

@login_required
def oauth_user_auth(request):
    oauth_server, oauth_request = initialize_server_request(request)
    
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE
        
    try:
        token = oauth_server.fetch_request_token(oauth_request)
    except oath.OAuthError, err:
        return send_oauth_error(err)
        
    try:
        callback = oauth_server.get_callback(oauth_request)
    except:
        callback = None
        
    if request.method == "GET":
        request.session['oauth'] = token.key
        params = oauth_request.get_normalized_parameters()
        return oauth_auth_view(request, token, callback, params)
    elif request.method == "POST":
        if request.session.get('oauth', '') == token.key:
            request.session['oauth'] = ''
            
            try:
                if int(request.POST.get('authorize_access')):
                    token = oauth_server.authorize_token(token, request.user)
                    args = token.to_string(only_key=True)
                else:
                    args = 'error=%s' % 'Access not granted by user.'
                
                response = HttpResponse('Fake callback.')
                    
            except OAuthError, err:
                response = send_oauth_error(err)
        else:
            response = HttpResponse('Action not allowed.')
            
        return response

def oauth_access_token(request):
    oauth_server, oauth_request = initialize_server_request(request)
    
    if oauth_request is None:
        return INVALID_PARAMS_RESPONSE
        
    try:
        token = oauth_server.fetch_access_token(oauth_request)
        return HttpResponse(token.to_string())
    except oauth.OAuthError, err:
        return send_oauth_error(err)

def oauth_protected_area(request):
    oauth_server, oauth_request = initialize_server_request(request)

    try:
        consumer, token, parameters = oauth_server.verify_request(oauth_request)
        return HttpResponse("protected resource, consumer=%s, token=%s, parameters=%s, you are=%s" % (consumer, token, parameters, token.user))
    except oauth.OAuthError, err:
        return send_oauth_error(err)

    return HttpResponse("OK = %s" % ok)
                
INVALID_PARAMS_RESPONSE = send_oauth_error(oauth.OAuthError('Invalid request parameters.'))
                
class OAuthAuthentication(object):
    """
    OAuth authentication. Based on work by Leah Culver.
    """
    def __init__(self, realm='Bitbucket.org HTTP'):
        self.realm = realm
        self.builder = oauth.build_authenticate_header
    
    def is_authenticated(self, request):
        """
        Checks whether a means of specifying authentication
        is provided, and if so, if it is a valid token.
        
        Read the documentation on `HttpBasicAuthentication`
        for more information about what goes on here.
        """
        if self.is_valid_request(request):
            try:
                consumer, token, parameters = self.validate_token(request)
            except oauth.OAuthError, err:
                return False

            if consumer and token:
                request.user = token.user
                return True
        else:
            print "INVALID REQUEST"
            print request
            
        return False
        
    def challenge(self):
        """
        Returns a 401 response with a small bit on
        what OAuth is, and where to learn more about it.
        
        When this was written, browsers did not understand
        OAuth authentication on the browser side, and hence
        the helpful template we render. Maybe some day in the
        future, browsers will take care of this stuff for us
        and understand the 401 with the realm we give it.
        """
        response = HttpResponse()
        response.status_code = 401
        realm = 'Bitbucket.org OAuth'

        for k, v in self.builder(realm=realm).iteritems():
            response[k] = v

        tmpl = loader.render_to_string('oauth/challenge.html',
            { 'MEDIA_URL': settings.MEDIA_URL })

        response.content = tmpl

        return response
        
    @staticmethod
    def is_valid_request(request):
        """
        Checks whether the required parameters are either in
        the http-authorization header sent by some clients,
        which is by the way the preferred method according to
        OAuth spec, but otherwise fall back to `GET` and `POST`.
        """
        must_have = [ 'oauth_'+s for s in [
            'consumer_key', 'token', 'signature',
            'signature_method', 'timestamp', 'nonce' ] ]
        
        is_in = lambda l: False not in [ (p in l) for p in must_have ]

        auth_params = request.META.get("HTTP_AUTHORIZATION", "")
        req_params = request.REQUEST
             
        return is_in(auth_params) or is_in(req_params)
        
    @staticmethod
    def validate_token(request, check_timestamp=True, check_nonce=True):
        oauth_server, oauth_request = initialize_server_request(request)
        return oauth_server.verify_request(oauth_request)
        