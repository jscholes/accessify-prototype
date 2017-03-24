from enum import Enum
import logging

from functional import seq

from . import structures


logger = logging.getLogger(__name__)


class SearchController:
    def __init__(self, api_client):
        self.api_client = api_client

    def perform_new_search(self, query, search_type):
        search_type = search_type.value
        logger.debug('Searching for {0} (search type: {1})'.format(query, search_type))
        results = self.api_client.search(query, search_type)
        if results:
            return (seq(results['tracks']['items'])
                .map(deserialize_item)
            )
        else:
            return []


def deserialize_item(item):
    artist_node = item['artists'][0]
    artist = structures.Artist(name=artist_node['name'], uri=artist_node['uri'])
    album_node = item['album']
    album = structures.Album(artist=artist, name=album_node['name'], uri=album_node['uri'])
    track = structures.Track(artist=artist, name=item['name'], uri=item['uri'], album=album, length=item['duration_ms'] / 1000)
    return track


class SearchType(Enum):
    TRACK = 'track'
    ARTIST = 'artist'
    ALBUM = 'album'
    PLAYLIST = 'playlist'
    USER = 'user'

