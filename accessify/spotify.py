from ctypes import windll
# TODO: Use ujson for faster JSON processing
import json
import random
import string

import psutil
import requests

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


def play_pause():
    send_command(CMD_PLAY_PAUSE)


def previous_track():
    send_command(CMD_PREV_TRACK)


def next_track():
    send_command(CMD_NEXT_TRACK)


def seek_backwards():
    send_command(CMD_SEEK_BACKWARD)


def seek_forwards():
    send_command(CMD_SEEK_FORWARD)


def decrease_volume():
    send_command(CMD_VOLUME_DOWN)


def increase_volume():
    send_command(CMD_VOLUME_UP)


def send_command(command_id):
    hwnd = find_window(SPOTIFY_WINDOW_CLASS, None)
    if hwnd == 0:
        raise SpotifyNotRunningError
    send_message(hwnd, WM_COMMAND, command_id, 0)


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


class SpotifyNotRunningError(Exception):
    """Raised when the HWND of the Spotify main window cannot be found."""
