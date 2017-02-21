from collections import defaultdict
from ctypes import windll
# TODO: Use ujson for faster JSON processing
import json
import queue
import random
import socket
import string
import threading
import time

import psutil
import requests
from requests.adapters import DEFAULT_POOLBLOCK, HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.connectionpool import HTTPSConnectionPool
from requests.packages.urllib3.connection import HTTPSConnection
from requests.packages.urllib3.util.timeout import Timeout

import structures

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

WM_COMMAND = 0x111
find_window = windll.User32.FindWindowW
send_message = windll.User32.SendMessageW

SPOTIFY_WINDOW_CLASS = 'SpotifyMainWindow'
WEB_HELPER_PROCESS = 'SpotifyWebHelper.exe'
SPOTIFY_PROCESS = 'Spotify.exe'
SPOTIFY_OPEN_TOKEN_URL = 'https://open.spotify.com/token'

CMD_PLAY_PAUSE = 114
CMD_PREV_TRACK = 116
CMD_NEXT_TRACK = 115
CMD_SEEK_BACKWARD = 118
CMD_SEEK_FORWARD = 117
CMD_VOLUME_UP = 121
CMD_VOLUME_DOWN = 122

EVENT_PLAY = 1
EVENT_PAUSE = 2
EVENT_TRACK_CHANGE = 3

STATE_UNDETERMINED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2


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
        return connections[0].laddr[1]


class RemoteBridge:
    """
    A Python interface to the remote bridge services hosted by the Spotify Web Helper.
    """

    def __init__(self, port):
        self._control_hostname = self.generate_hostname()
        self._event_manager_hostname = self.generate_hostname()
        self._port = port
        self.event_manager = EventManager(self)
        self._connected = threading.Event()
        self._command_queue = queue.Queue()
        command_consumer = CommandConsumer(self._command_queue, self._connected)
        command_consumer.start()
        adapter = SpotifyRemoteAdapter(self._connected)
        self._session = requests.Session()
        self._session.headers.update({'Origin': 'https://open.spotify.com'})
        self._session.verify = False
        self._session.mount('https://{0}'.format(self._event_manager_hostname), adapter)
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
            return self.remote_request('status', params=params, hostname=hostname)
        else:
            return self.remote_request('status', hostname=hostname)

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
        return self._session.get(request_url, params=request_params).json()

    def generate_hostname(self):
        subdomain = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        return '{0}.spotilocal.com'.format(subdomain)

    def get_csrf_token(self):
        url = 'https://{0}:{1}/simplecsrf/token.json'.format(self._control_hostname, self._port)
        response = self._session.get(url)
        data = response.json()
        return data['token']

    def get_oauth_token(self):
        response = self._session.get(SPOTIFY_OPEN_TOKEN_URL)
        data = response.json()
        return data['t']

    def send_command(self, command_id):
        self._command_queue.put(command_id)


class SpotifyRemoteAdapter(HTTPAdapter):
    def __init__(self, connected_event, *args, **kwargs):
        self.connected_event = connected_event
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs):
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        pool_kwargs.update(connected_event=self.connected_event)
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, strict=True, **pool_kwargs)
        # Avoid updating global state
        self.poolmanager.pool_classes_by_scheme = self.poolmanager.pool_classes_by_scheme.copy()
        self.poolmanager.pool_classes_by_scheme.update(https=SpotifyRemoteConnectionPool)


class SpotifyRemoteConnection(HTTPSConnection):
    def __init__(self, host, port=None, key_file=None, cert_file=None, strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, ssl_context=None, **kw):
        if not getattr(self, 'connected_event', None):
            self.connected_event = kw.pop('connected_event')
        super().__init__(host, port, strict=strict, timeout=timeout)

    def endheaders(self, *args, **kwargs):
        super().endheaders(*args, **kwargs)
        self.connected_event.set()


class SpotifyRemoteConnectionPool(HTTPSConnectionPool):
    ConnectionCls = SpotifyRemoteConnection


class EventManager(threading.Thread):
    def __init__(self, remote_bridge, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDaemon(True)
        self._remote_bridge = remote_bridge
        self._event_queue = queue.Queue()
        self._event_consumer = EventConsumer(self._event_queue)

    def subscribe(self, event_type, callback):
        self._event_consumer.subscribe(event_type, callback)

    def run(self):
        self._event_consumer.start()
        # Get initial status
        status = self._remote_bridge.get_status(from_event_manager=True)
        self._event_queue.put(status)
        # Then poll for changes
        while True:
            status = self._remote_bridge.get_status(return_after=60, from_event_manager=True)
            self._event_queue.put(status)


class EventConsumer(threading.Thread):
    def __init__(self, event_queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDaemon(True)
        self._event_queue = event_queue
        self._callbacks = defaultdict(lambda: [])
        self._current_track = None
        self._playback_state = STATE_UNDETERMINED

    def subscribe(self, event_type, callback):
        self._update_subscriber(event_type, callback)
        self._callbacks[event_type].append(callback)

    def run(self):
        while True:
            status = self._event_queue.get()
            self._process_update(status)

    def _process_update(self, status_dict):
        # TODO: Handle errors
        # Remove the keys we're not really interested in
        for key in ('version', 'play_enabled', 'prev_enabled', 'next_enabled', 'open_graph_state', 'context', 'online', 'server_time'):
            status_dict.pop(key)
        track = deserialize_track(status_dict.pop('track'))
        if track != self._current_track:
            self._current_track = track
            self._update_subscribers(EVENT_TRACK_CHANGE)
        playing = status_dict['playing']
        playback_state = STATE_PLAYING if playing else STATE_PAUSED
        if playback_state != self._playback_state:
            if playback_state == STATE_PLAYING:
                self._update_subscribers(EVENT_PLAY)
            elif playback_state == STATE_PAUSED:
                self._update_subscribers(EVENT_PAUSE)
            self._playback_state = playback_state

    def _update_subscribers(self, event_type):
        for callback in self._callbacks[event_type]:
            self._update_subscriber(event_type, callback)

    def _update_subscriber(self, event_type, callback):
        if event_type == EVENT_TRACK_CHANGE and self._current_track is not None:
            callback(self._current_track)
        elif event_type in (EVENT_PLAY, EVENT_PAUSE):
            callback()


class CommandConsumer(threading.Thread):
    def __init__(self, command_queue, connected_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDaemon(True)
        self._command_queue = command_queue
        self._connected_event = connected_event

    def run(self):
        self._connected_event.wait()
        while True:
            command = self._command_queue.get()
            self._send_command(command)
            if command in (CMD_PLAY_PAUSE, CMD_PREV_TRACK, CMD_NEXT_TRACK):
                time.sleep(0.3)

    def _send_command(self, command_id):
        hwnd = find_window(SPOTIFY_WINDOW_CLASS, None)
        if hwnd == 0:
            raise SpotifyNotRunningError
        send_message(hwnd, WM_COMMAND, command_id, 0)


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
