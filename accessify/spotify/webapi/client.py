import os.path

import requests
import ujson as json


BASE_URL = 'https://api.spotify.com'
API_VERSION = 'v1'


class WebAPIClient:
    def __init__(self, access_token):
        self._session = requests.Session()
        self._session.headers.update({'Authorization': 'Bearer {0}'.format(access_token)})

    def me(self):
        return self.request('me')

    def search(self, query, search_type):
        return self.request('search', query_parameters={'q': query, 'type': search_type, 'market': 'GB'})

    def request(self, endpoint, method='GET', query_parameters=None):
        if query_parameters is None:
            query_parameters = {}
        response = self._session.request(method, url=api_url(endpoint), params=query_parameters)
        return json.loads(response.content)


def api_url(endpoint):
    return '{0}/{1}/{2}'.format(BASE_URL, API_VERSION, endpoint)


class TestWebAPIClient:
    def search(self, query, search_type):
        # This code won't last for long
        module_dir, _ = os.path.split(__file__)
        json_path = os.path.join(module_dir, 'searchresponses')
        filename = '{0}-{1}.json'.format(search_type, query.lower().replace(' ', '_'))
        try:
            with open(os.path.join(json_path, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, ValueError):
            return {} # No results
        return data

