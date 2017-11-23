import base64
import logging
import threading

import flask
import requests
import ujson as json

from requests.models import RequestEncodingMixin
from requests.utils import requote_uri

from accessify.spotify.webapi import exceptions


logger = logging.getLogger(__name__)

TOKEN_URL = 'https://accounts.spotify.com/api/token'
AUTHORISATION_URL = 'https://accounts.spotify.com/authorize?{params}'

ALL_SCOPES = ['playlist-read-private', 'playlist-read-collaborative', 'playlist-modify-public', 'playlist-modify-private', 'user-follow-modify', 'user-follow-read', 'user-library-read', 'user-library-modify', 'user-read-private', 'user-read-birthdate', 'user-read-email', 'user-top-read', 'user-read-recently-played', 'user-read-playback-state', 'user-modify-playback-state', 'user-read-currently-playing', 'streaming', 'ugc-image-upload']
CALLBACK_SERVER_PORT = 43612


class AuthorisationAgent:
    def __init__(self, client_id, client_secret, access_token=None, refresh_token=None, requests_session=None):
        self.client_id = client_id
        self._client_secret = client_secret
        self.access_token = access_token
        self._refresh_token = refresh_token
        if requests_session is None:
            requests_session = requests.Session()
        self.session = requests_session

    def get_access_token(self):
        if self.access_token is None:
            raise exceptions.NotAuthenticatedError
        else:
            return self.access_token

    def get_refresh_token(self):
        return self._refresh_token

    def set_access_token(self, token):
        self.access_token = token

    def set_refresh_token(self, token):
        self._refresh_token = token

    def fetch_access_token(self, auth_code, redirect_uri):
        logger.debug('Fetching access token...')
        params = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': redirect_uri,
        }
        self._token_request(params)

    def refresh_access_token(self):
        logger.debug('Attempting to refresh expired access token')
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self._refresh_token,
        }
        self._token_request(params)

    def _token_request(self, params):
        auth_string = base64.b64encode(bytes('{0}:{1}'.format(self.client_id, self._client_secret), 'utf-8'))
        auth_header = 'Basic {0}'.format(auth_string.decode('utf-8'))
        headers = {
            'Authorization': auth_header,
        }
        try:
            response = self.session.post(TOKEN_URL, headers=headers, data=params)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            logger.error('HTTP/{0} error during web API request:\n{1}'.format(response.status_code, response.content), exc_info=True)
        payload = json.loads(response.content)
        self.access_token = payload['access_token']
        try:
            self._refresh_token = payload['refresh_token']
        except KeyError:
            pass


class OAuthCallbackServer:
    def __init__(self, client_id, auth_code_callback, errback=None, port=CALLBACK_SERVER_PORT):
        self.client_id = client_id
        self.port = port
        self.auth_code_callback = auth_code_callback
        self.errback = errback

        self._server = flask.Flask('OAuthCallbackServer')
        self._server.add_url_rule('/oauth', view_func=self.on_callback_request)

    def on_callback_request(self):
        auth_code = flask.request.args.get('code', None)
        if auth_code is None and self.errback is not None:
            self.errback(flask.request.args.get('error', None))
        else:
            self.auth_code_callback(auth_code)

        self.shutdown()
        return ''

    def shutdown(self):
        flask.request.environ.get('werkzeug.server.shutdown')()

    def run_threaded(self):
        threading.Thread(target=self._server.run, kwargs={'port': self.port, 'debug': False}).start()

    def get_authorisation_url(self, scopes):
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.get_redirect_uri(),
            'scope': ' '.join(scopes),
        }
        return requote_uri(AUTHORISATION_URL.format(params=RequestEncodingMixin._encode_params(params)))

    def get_redirect_uri(self):
        return 'http://127.0.0.1:{0}/oauth'.format(self.port)

