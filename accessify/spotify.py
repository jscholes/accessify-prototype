from collections import defaultdict
from enum import Enum
# TODO: Use ujson for faster JSON processing
import json
import logging
import queue
import random
import string
import threading
import time
from ctypes import windll

import psutil
import requests

from concurrency import consume_queue
import structures


logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

WM_COMMAND = 0x111
find_window = windll.User32.FindWindowW
send_message = windll.User32.SendMessageW

SPOTIFY_WINDOW_CLASS = 'SpotifyMainWindow'
WEB_HELPER_PROCESS = 'SpotifyWebHelper.exe'
SPOTIFY_PROCESS = 'Spotify.exe'
SPOTIFY_OPEN_TOKEN_URL = 'https://open.spotify.com/token'

spotify_remote_errors = defaultdict(lambda: 'Unknown error', {
    '4001': 'Unknown method',
    '4002': 'Error parsing request',
    '4003': 'Unknown service',
    '4004': 'Service not responding',
    '4102': 'Invalid OAuthToken',
    '4103': 'Expired OAuth token',
    '4104': 'OAuth token not verified',
    '4105': 'Token verification denied too many requests',
    '4106': 'Token verification timeout',
    '4107': 'Invalid Csrf token',
    '4108': 'OAuth token is invalid for current user',
    '4109': 'Invalid Csrf path',
    '4110': 'No user logged in',
    '4111': 'Invalid scope',
    '4112': 'Csrf challenge failed',
    '4201': 'Upgrade to premium',
    '4202': 'Upgrade to premium or wait',
    '4203': 'Billing failed',
    '4204': 'Technical error',
    '4205': 'Commercial is playing',
    '4301': 'Content is unavailable but can be purchased',
    '4302': 'Premium only content',
    '4303': 'Content unavailable',
})


class PlaybackCommand(Enum):
    PLAY_PAUSE = 114
    PREV_TRACK = 116
    NEXT_TRACK = 115
    SEEK_BACKWARD = 118
    SEEK_FORWARD = 117
    VOLUME_UP = 121
    VOLUME_DOWN = 122


class EventType(Enum):
    PLAY = 1
    PAUSE = 2
    TRACK_CHANGE = 3
    ERROR = 4
    STOP = 5


class PlaybackState(Enum):
    UNDETERMINED = 0
    PLAYING = 1
    PAUSED = 2
    STOPPED = 3


def get_web_helper_port():
    """
    Attempt to find the HTTPS port that the SpotifyWebHelper process is listening on.

    If SpotifyWebHelper.exe is not running, raises SpotifyNotRunningError.  Otherwise returns the port number.
    """
    # TODO: Find the listening port for Spotify.exe if the Web Helper isn't running
    helper_process = None
    for process in psutil.process_iter():
        if process.name() == WEB_HELPER_PROCESS:
            helper_process = process
            break

    if helper_process is None:
        raise SpotifyNotRunningError
    else:
        connections = sorted(helper_process.connections(), key=lambda conn: conn.laddr[1])
        port = connections[0].laddr[1]
        logger.debug('WebHelper listening port: {0}'.format(port))
        return port


class RemoteBridge:
    """
    A Python interface to the remote bridge services hosted by the Spotify Web Helper.
    """

    def __init__(self, port):
        self._control_hostname = self.generate_hostname()
        self._event_manager_hostname = self.generate_hostname()
        self._port = port
        self._command_queue = queue.Queue()
        consume_queue(self._command_queue, self._send_command)
        self._session = requests.Session()
        self._session.headers.update({'Origin': 'https://open.spotify.com'})
        self._session.verify = False
        # These are lazy loaded when they're needed
        self._csrf_token = None
        self._oauth_token = None

    def get_status(self, return_after=None, from_event_manager=False):
        if from_event_manager:
            hostname = self._event_manager_hostname
        else:
            hostname = self._control_hostname
        if return_after is not None:
            params = {
                'returnafter': return_after,
                'returnon': 'login,logout,play,pause,error,ap',
            }
            response = self.remote_request('status', params=params, hostname=hostname)
        else:
            response = self.remote_request('status', hostname=hostname)
        # Do we have all the metadata we need?
        try:
            album = response['track']['album_resource']['name']
            artist = response['track']['artist_resource']['name']
            track_name = response['track']['track_resource']['name']
            track_length = response['track']['length']
        except KeyError:
            logger.error('Received incomplete metadata from Spotify')
            raise MetadataNotReadyError
        return response

    def play_uri(self, uri, context=None):
        params = {
            'uri': uri,
        }
        if context is not None:
            params.update(context=context)
        else:
            params.update(context=uri)
        return self.remote_request('play', params=params)

    def remote_request(self, endpoint, params=None, hostname=None):
        if hostname is None:
            hostname = self._control_hostname
        if self._csrf_token is None:
            self._csrf_token = self.get_csrf_token()
        if self._oauth_token is None:
            self._oauth_token = self.get_oauth_token()
        request_url = 'https://{0}:{1}/remote/{2}.json'.format(hostname, self._port, endpoint)
        request_params = {
            'oauth': self._oauth_token,
            'csrf': self._csrf_token,
        }
        if params is not None:
            request_params.update(params)
        logger.debug('Requesting URL: {0} with params: {1}'.format(request_url, request_params))
        response = self._session.get(request_url, params=request_params).json()
        logger.debug('Received response: {0}'.format(response))
        if 'error' in response:
            error_code = response['error']['type']
            error_description = spotify_remote_errors[error_code]
            logger.debug('Error {0} from Spotify: {1}'.format(error_code, error_description))
            raise SpotifyRemoteError(error_code, error_description)
        return response

    def generate_hostname(self):
        subdomain = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        return '{0}.spotilocal.com'.format(subdomain)

    def get_csrf_token(self):
        url = 'https://{0}:{1}/simplecsrf/token.json'.format(self._control_hostname, self._port)
        logger.debug('Requesting {0}'.format(url))
        response = self._session.get(url)
        data = response.json()
        logger.debug('CSRF request response: {0}'.format(data))
        return data['token']

    def get_oauth_token(self):
        response = self._session.get(SPOTIFY_OPEN_TOKEN_URL)
        data = response.json()
        logger.debug('OAuth token request response: {0}'.format(data))
        return data['t']

    def send_command(self, command):
        """
        Queue up a PlaybackCommand to be delivered to the Spotify window.

        The queued command will eventually be delivered by the _send_command method, which implements the actual logic.
        """
        logger.debug('Queuing command: {0}'.format(command))
        self._command_queue.put(command)

    def _send_command(self, command):
        hwnd = find_window(SPOTIFY_WINDOW_CLASS, None)
        if hwnd == 0:
            return
        logger.debug('Sending command {0} to window handle {1}'.format(command, hwnd))
        send_message(hwnd, WM_COMMAND, command.value, 0)
        if command in (PlaybackCommand.PLAY_PAUSE, PlaybackCommand.PREV_TRACK, PlaybackCommand.NEXT_TRACK):
            logger.debug('Sleeping to avoid command flooding')
            time.sleep(0.3)


class EventManager(threading.Thread):
    def __init__(self, remote_bridge, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDaemon(True)
        self._remote_bridge = remote_bridge
        self._event_queue = queue.Queue()
        self._callbacks = defaultdict(lambda: [])
        self._previous_track_dict = {}
        self._playback_state = PlaybackState.UNDETERMINED
        self._in_error_status = False

    def subscribe(self, event_type, callback):
        logger.debug('Subscribing callback {0} to {1}'.format(callback, event_type))
        self._callbacks[event_type].append(callback)

    def run(self):
        consume_queue(self._event_queue, self._process_item)
        return_immediately = True
        while True:
            try:
                if return_immediately:
                    status = self._remote_bridge.get_status(from_event_manager=True)
                else:
                    status = self._remote_bridge.get_status(return_after=60, from_event_manager=True)
                self._event_queue.put(status)
                return_immediately = False
            except MetadataNotReadyError:
                return_immediately = True
                continue
            except SpotifyRemoteError as e:
                self._event_queue.put(e)

    def _process_item(self, item):
        if isinstance(item, SpotifyRemoteError):
            if self._in_error_state:
                return
            else:
                self._in_error_state = True
                self._update_subscribers(EventType.ERROR, context=item)
                return
        self._process_status_dict(item)
        self._in_error_state = False

    def _process_status_dict(self, status_dict):
        # Remove the keys we're not really interested in
        for key in ('version', 'play_enabled', 'prev_enabled', 'next_enabled', 'open_graph_state', 'context', 'online', 'server_time'):
            status_dict.pop(key)
        track_dict = status_dict.pop('track')
        if track_dict != self._previous_track_dict:
            track = deserialize_track(track_dict)
            logger.debug('Deserialized track: {0}'.format(track))
            self._update_subscribers(EventType.TRACK_CHANGE, context=track)
            self._previous_track_dict = track_dict
        playing = status_dict['playing']
        if playing:
            playback_state = PlaybackState.PLAYING
        elif not playing and status_dict['playing_position'] == 0:
            playback_state = PlaybackState.STOPPED
        else:
            playback_state = PlaybackState.PAUSED
        if playback_state != self._playback_state:
            if playback_state == PlaybackState.PLAYING:
                self._update_subscribers(EventType.PLAY)
            elif playback_state == PlaybackState.PAUSED:
                self._update_subscribers(EventType.PAUSE)
            elif playback_state == PlaybackState.STOPPED:
                self._update_subscribers(EventType.STOP)
            self._playback_state = playback_state

    def _update_subscribers(self, event_type, context=None):
        logger.debug('Updating subscribers to {0} with context: {1}'.format(event_type, context))
        for callback in self._callbacks[event_type]:
            self._update_subscriber(event_type, callback, context)

    def _update_subscriber(self, event_type, callback, context=None):
        if context is not None:
            callback(context)
        else:
            callback()


def deserialize_track(track_dict):
    artist_res = track_dict['artist_resource']
    album_res = track_dict['album_resource']
    track_res = track_dict['track_resource']
    artist = structures.Artist(artist_res['name'], artist_res['uri'])
    album = structures.Album(artist, album_res['name'], album_res['uri'])
    track = structures.Track(artist, album, track_res['name'], track_dict['length'], track_dict['track_type'], track_res['uri'])
    return track


class SpotifyNotRunningError(Exception):
    """Raised when the HWND of the Spotify main window cannot be found."""


class SpotifyRemoteError(Exception):
    """Raised when the Spotify remote service returns an error code."""

    def __init__(self, error_code, error_description, *args, **kwargs):
        self.error_code = error_code
        self.error_description = error_description


class MetadataNotReadyError(Exception):
    """Raised when Spotify has started playing a track, but the track resource hasn't been fully populated with metadata yet."""

