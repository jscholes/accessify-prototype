from enum import Enum
import logging

from functional import seq

from . import structures


logger = logging.getLogger(__name__)


class SearchController:
    def __init__(self, api_client, thread_pool_executor):
        self.api_client = api_client
        self.executor = thread_pool_executor

    def perform_new_search(self, query, search_type, results_callback):
        def done_cb(future):
            try:
                results_callback(future.result())
            except Exception:
                logger.error('Error while searching', exc_info=True)

        future = self.executor.submit(self._perform_new_search, query, search_type)
        future.add_done_callback(done_cb)

    def _perform_new_search(self, query, search_type):
        logger.debug('Searching for {0} (search type: {1})'.format(query, search_type))
        results = self.api_client.search(query, search_type.value)
        if results:
            container = item_containers[search_type]
            deserializer = item_deserializers[search_type]
            return (seq(results[container]['items'])
                .map(deserializer)
            )
        else:
            return []


def deserialize_track(track):
    artists = seq(track['artists']).map(deserialize_artist)
    album = deserialize_album(track['album'])
    return structures.Track(artists=artists, name=track['name'], uri=track['uri'], album=album, length=track['duration_ms'] / 1000)


def deserialize_album(album):
    artists = seq(album['artists']).map(deserialize_artist)
    return structures.Album(artists=artists, name=album['name'], uri=album['uri'])


def deserialize_artist(artist):
    return structures.Artist(name=artist['name'], uri=artist['uri'])


def deserialize_playlist(playlist):
    return structures.Playlist(name=playlist['name'], total_tracks=playlist['tracks']['total'], uri=playlist['uri'])


class SearchType(Enum):
    TRACK = 'track'
    ARTIST = 'artist'
    ALBUM = 'album'
    PLAYLIST = 'playlist'


item_containers = {
    SearchType.TRACK: 'tracks',
    SearchType.ALBUM: 'albums',
    SearchType.ARTIST: 'artists',
    SearchType.PLAYLIST: 'playlists',
}


# TODO: Probably a better way of doing this
item_deserializers = {
    SearchType.TRACK: deserialize_track,
    SearchType.ALBUM: deserialize_album,
    SearchType.ARTIST: deserialize_artist,
    SearchType.PLAYLIST: deserialize_playlist,
}

