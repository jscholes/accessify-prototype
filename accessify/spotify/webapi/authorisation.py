import requests

from . import exceptions


class AuthorisationAgent:
    def __init__(self, client_id, client_secret, access_token=None, refresh_token=None, requests_session=None):
        self.client_id = client_id
        self._client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = None
        if requests_session is None:
            requests_session = requests.Session()
        self.session = requests_session

    def get_access_token(self):
        if self.access_token is None:
            raise exceptions.NotAuthenticatedError
        else:
            return self.access_token

