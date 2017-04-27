import base64
import logging

import requests
import ujson as json

from accessify.spotify.webapi import exceptions


logger = logging.getLogger(__name__)

TOKEN_URL = 'https://accounts.spotify.com/api/token'


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

    def refresh_access_token(self):
        logger.debug('Attempting to refresh expired access token')
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self._refresh_token,
        }
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

