from collections import defaultdict
from ctypes import windll
# TODO: Use ujson for faster JSON processing
import json
import queue
import random
import string
import threading

import psutil
import requests

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
        self._port = port
        self._session = requests.Session()
        self._session.headers.update({'Origin': 'https://open.spotify.com'})
        self._session.verify = False
        self.event_manager = EventManager(self)
        # These are lazy loaded when they're needed
        self._hostname = None
        self._csrf_token = None
        self._oauth_token = None

    def get_status(self, return_after=None):
        if return_after is not None:
            params = {
                'returnafter': return_after,
                'returnon': 'login,logout,play,pause,error,ap',
            }
            return self.remote_request('status', params=params)
        else:
            return self.remote_request('status')

    def play_uri(self, uri, context=None):
        params = {
            'uri': uri,
        }
        if context is not None:
            params.update(context=context)
        else:
            params.update(context=uri)
        return self.remote_request('play', params=params)

    def play_pause(self):
        self.send_command(CMD_PLAY_PAUSE)

    def previous_track(self):
        self.send_command(CMD_PREV_TRACK)

    def next_track(self):
        self.send_command(CMD_NEXT_TRACK)

    def seek_backwards(self):
        self.send_command(CMD_SEEK_BACKWARD)

    def seek_forwards(self):
        send_command(CMD_SEEK_FORWARD)

    def decrease_volume(self):
        self.send_command(CMD_VOLUME_DOWN)

    def increase_volume(self):
        self.send_command(CMD_VOLUME_UP)

    def send_command(self, command_id):
        hwnd = find_window(SPOTIFY_WINDOW_CLASS, None)
        if hwnd == 0:
            raise SpotifyNotRunningError
        send_message(hwnd, WM_COMMAND, command_id, 0)

    def remote_request(self, endpoint, params=None):
        if self._hostname is None:
            self._hostname = self.generate_hostname()
        if self._csrf_token is None:
            self._csrf_token = self.get_csrf_token()
        if self._oauth_token is None:
            self._oauth_token = self.get_oauth_token()
        request_url = 'https://{0}:{1}/remote/{2}.json'.format(self._hostname, self._port, endpoint)
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
        url = 'https://{0}:{1}/simplecsrf/token.json'.format(self._hostname, self._port)
        response = self._session.get(url)
        data = response.json()
        return data['token']

    def get_oauth_token(self):
        response = self._session.get(SPOTIFY_OPEN_TOKEN_URL)
        data = response.json()
        return data['t']


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
        status = self._remote_bridge.get_status()
        self._event_queue.put(status)
        # Then poll for changes
        while True:
            status = self._remote_bridge.get_status(return_after=60)
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
