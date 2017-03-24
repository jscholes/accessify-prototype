from enum import Enum
import logging

from functional import seq

from . import structures


logger = logging.getLogger(__name__)


class SearchController:
    def __init__(self, api_client):
        self.api_client = api_client

    def perform_new_search(self, query, search_type):
        logger.debug('Searching for {0} (search type: {1})'.format(query, search_type))
        results = self.api_client.search(query, search_type.value)
        if results:
            return (seq(results['tracks']['items'])
                .map(deserialize_item)
            )
        else:
            return []


def deserialize_item(item):
    artists_node = item['artists']
    artists = []
    for artist in artists_node:
        artists.append(structures.Artist(name=artist['name'], uri=artist['uri']))
    album_node = item['album']
    album = structures.Album(artists=[artist], name=album_node['name'], uri=album_node['uri'])
    track = structures.Track(artists=artists, name=item['name'], uri=item['uri'], album=album, length=item['duration_ms'] / 1000)
    return track


class SearchType(Enum):
    TRACK = 'track'
    ARTIST = 'artist'
    ALBUM = 'album'
    PLAYLIST = 'playlist'

