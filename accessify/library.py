from enum import Enum
import logging

import pykka
from functional import seq

from accessify import structures


logger = logging.getLogger(__name__)


class LibraryController(pykka.ThreadingActor):
    use_daemon_thread = True

    def __init__(self, config, api_client):
        super().__init__()
        self.config = config
        self.api_client = api_client

    def on_start(self):
        profile = self.api_client.me()
        logger.info('Logged into Spotify as {0} (account type {1})'.format(profile['id'], profile['product']))

    def on_stop(self):
        self.config.update({
            'spotify_access_token': self.api_client.authorisation.get_access_token(),
            'spotify_refresh_token': self.api_client.authorisation.get_refresh_token(),
        })

    def perform_new_search(self, query, search_type, results_callback):
        results = self.perform_search(query, search_type, offset=0)
        results_callback(results)

    def perform_search(self, query, search_type, offset):
        results = self.api_client.search(query, search_type.value, offset=offset)
        if results:
            container = item_containers[search_type]
            deserializer = item_deserializers[search_type]
            entities = results[container]
            deserialized_results = seq(entities['items']).map(deserializer)
            result_collection = structures.ItemCollection(items=list(deserialized_results), total=entities['total'])
        else:
            result_collection = structures.ItemCollection(items=[], total=0)

        return result_collection


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

