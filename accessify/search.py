from enum import Enum
import logging

import pykka
from functional import seq

from . import structures


logger = logging.getLogger(__name__)


class SearchController(pykka.ThreadingActor):
    use_daemon_thread = True

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    def on_start(self):
        profile = self.api_client.me()
        logger.info('Logged into Spotify as {0} (account type {1})'.format(profile['id'], profile['product']))

    def perform_new_search(self, query, search_type, results_callback):
        results = self.api_client.search(query, search_type.value)
        if results:
            container = item_containers[search_type]
            deserializer = item_deserializers[search_type]
            deserialized_results = seq(results[container]['items']).map(deserializer)
        else:
            deserialized_results = []

        results_callback(deserialized_results)


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

