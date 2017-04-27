from enum import Enum
import logging
import webbrowser

import pykka
from functional import seq

from accessify import structures

from accessify.signalling import Signalman
from accessify.spotify.webapi import authorisation


logger = logging.getLogger(__name__)


class LibraryController(pykka.ThreadingActor):
    use_daemon_thread = True

    def __init__(self, signalman, config, api_client):
        super().__init__()
        self._signalman = signalman
        self.config = config
        self.api_client = api_client

    def on_stop(self):
        self.config.update({
            'spotify_access_token': self.api_client.authorisation.get_access_token(),
            'spotify_refresh_token': self.api_client.authorisation.get_refresh_token(),
        })

    def log_in(self):
        access_token = self.config.get('spotify_access_token')
        refresh_token = self.config.get('spotify_refresh_token')
        if not access_token or not refresh_token:
            self._signalman.authorisation_required.send(False)
        else:
            self.complete_authorisation(access_token, refresh_token)

    def begin_authorisation(self):
        auth_callback = self.actor_ref.proxy().on_authorisation_code_received
        self.authorisation_server = authorisation.OAuthCallbackServer(self.api_client.authorisation.client_id, auth_callback)
        self.authorisation_server.run_threaded()
        webbrowser.open(self.authorisation_server.get_authorisation_url(authorisation.ALL_SCOPES))

    def on_authorisation_code_received(self, code):
        logger.debug('Received auth code: {0}'.format(code))
        self.api_client.authorisation.fetch_access_token(code, self.authorisation_server.get_redirect_uri())
        self.load_profile()

    def complete_authorisation(self, access_token, refresh_token):
        self.api_client.authorisation.set_access_token(access_token)
        self.api_client.authorisation.set_refresh_token(refresh_token)
        self.load_profile()

    def load_profile(self):
        profile = self.api_client.me()
        logger.info('Logged into Spotify as {0} (account type {1})'.format(profile['id'], profile['product']))
        self._signalman.authorisation_completed.send(profile)

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


item_deserializers = {
    SearchType.TRACK: deserialize_track,
    SearchType.ALBUM: deserialize_album,
    SearchType.ARTIST: deserialize_artist,
    SearchType.PLAYLIST: deserialize_playlist,
}


class LibrarySignalman(Signalman):
    signals = ['authorisation_required', 'authorisation_completed', 'authorisation_error']

