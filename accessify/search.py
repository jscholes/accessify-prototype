from collections import defaultdict
from enum import Enum
import logging

from . import structures


logger = logging.getLogger(__name__)


class SearchController:
    def __init__(self, api_client):
        self.api_client = api_client

    def perform_new_search(self, query, search_type):
        logger.debug('Searching for {0} in {1}'.format(query, search_type))
        return self.api_client.search(query, search_type)


class SearchType(Enum):
    TRACK = 'track'
    ARTIST = 'artist'
    ALBUM = 'album'
    PLAYLIST = 'playlist'
    USER = 'user'

