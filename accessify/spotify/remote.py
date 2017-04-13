from collections import defaultdict
from enum import Enum
import logging
import random
import string
import threading
import time
from ctypes import windll

from requests.packages.urllib3 import disable_warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import psutil
import requests
from functional import seq
import ujson as json

from accessify.spotify import exceptions


logger = logging.getLogger(__name__)

disable_warnings(InsecureRequestWarning)

find_window = windll.User32.FindWindowW
send_message = windll.User32.SendMessageW

WM_COMMAND = 0x111
SPOTIFY_WINDOW_CLASS = 'SpotifyMainWindow'
SPOTIFY_PROCESSES = ('Spotify.exe', 'SpotifyWebHelper.exe')
SPOTIFY_PORT_RANGE = range(4370, 4380)
SPOTIFY_OPEN_TOKEN_URL = 'https://open.spotify.com/token'


class RemoteBridge:
    """
    A Python interface to the remote bridge services hosted by the Spotify Web Helper.
    """

    def __init__(self, port):
        self._hostname = self.generate_hostname()
        self._port = port
        self._session = requests.Session()
        self._session.headers.update({'Origin': 'https://open.spotify.com'})
        self._session.verify = False
        # These are lazy loaded when they're needed
        self._csrf_token = None
        self._oauth_token = None

    def get_status(self, return_after=None):
        if return_after is not None:
            params = {
                'returnafter': return_after,
                'returnon': 'login,logout,play,pause,error,ap',
            }
            response = self.remote_request('status', params=params)
        else:
            response = self.remote_request('status')
        # Do we have all the metadata we need?
        # TODO: If track type is "other", this is probably a podcast and we should ignore it.
        try:
            album = response['track']['album_resource']['name']
            artist = response['track']['artist_resource']['name']
            track_name = response['track']['track_resource']['name']
            track_length = response['track']['length']
        except KeyError:
            logger.error('Received incomplete metadata from Spotify')
            raise exceptions.MetadataNotReadyError
        return response

    def play_uri(self, uri, context=None):
        params = {
            'uri': uri,
        }
        if context is not None:
            params.update(context=context)
        else:
            params.update(context=uri)
        try:
            return self.remote_request('play', params=params)
        except exceptions.SpotifyRemoteError as e:
            if e.error_code in ('4204', '4205', '4301', '4302', '4303'):
                raise exceptions.ContentPlaybackError
            else:
                raise

    def remote_request(self, endpoint, params=None, service='remote', authenticated=True):
        request_url = 'https://{0}:{1}/{2}/{3}.json'.format(self._hostname, self._port, service, endpoint)
        if authenticated:
            if self._csrf_token is None:
                self._csrf_token = self.get_csrf_token()
            if self._oauth_token is None:
                self._oauth_token = self.get_oauth_token()
            request_params = {
                'oauth': self._oauth_token,
                'csrf': self._csrf_token,
            }
        else:
            request_params = {}
        if params is not None:
            request_params.update(params)
        logger.debug('Requesting URL: {0} with params: {1}'.format(request_url, request_params))
        try:
            response = self._session.get(request_url, params=request_params)
        except requests.exceptions.ConnectionError:
            raise exceptions.SpotifyConnectionError
        response_content = json.loads(response.content)
        logger.debug('Received response: {0}'.format(response_content))
        if 'error' in response_content:
            error_code = response_content['error']['type']
            error_description = spotify_remote_errors[error_code]
            logger.debug('Error {0} from Spotify: {1}'.format(error_code, error_description))
            raise exceptions.SpotifyRemoteError(error_code, error_description)
        return response_content

    def generate_hostname(self):
        subdomain = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        return '{0}.spotilocal.com'.format(subdomain)

    def get_csrf_token(self):
        response = self.remote_request('token', service='simplecsrf', authenticated=False)
        return response['token']

    def get_oauth_token(self):
        response = self._session.get(SPOTIFY_OPEN_TOKEN_URL)
        data = json.loads(response.content)
        logger.debug('OAuth token request response: {0}'.format(data))
        return data['t']

    def send_command(self, command):
        hwnd = find_window(SPOTIFY_WINDOW_CLASS, None)
        if hwnd == 0:
            return
        logger.debug('Sending command {0} to window handle {1}'.format(command, hwnd))
        send_message(hwnd, WM_COMMAND, command.value, 0)
        if command in (PlaybackCommand.PLAY_PAUSE, PlaybackCommand.PREV_TRACK, PlaybackCommand.NEXT_TRACK):
            logger.debug('Sleeping to avoid command flooding')
            time.sleep(0.3)


def find_listening_port():
    """
    Attempt to find the HTTPS port that the SpotifyWebHelper process is listening on.

    If SpotifyWebHelper.exe is not running, this function will atempt to find the listening port for Spotify.exe as a backup.  If neither process is running, exceptions.SpotifyNotRunningError will be raised.  Otherwise it will return the port number which is guaranteed to be between 4370 and 4380 (not inclusive).
    """
    # Find all Spotify processes with at least one active connection
    spotify_processes = (seq(psutil.process_iter())
        .filter(lambda proc: proc.name() in SPOTIFY_PROCESSES and any(proc.connections()))
    )

    if not spotify_processes:
        raise exceptions.SpotifyNotRunningError

    # Find the first Spotify connection listening on ports 4370-4379
    try:
        connection = (seq(proc.connections() for proc in spotify_processes)
            .flatten()
            .filter(lambda conn: conn.status == 'LISTEN' and conn.laddr[1] in SPOTIFY_PORT_RANGE)
            .sorted(key=lambda conn: conn.laddr[1])
            .first()
        )
    except IndexError:
        raise exceptions.SpotifyNotRunningError

    host, port = connection.laddr
    logger.debug('Spotify listening on port {0}'.format(port))
    return port


class PlaybackCommand(Enum):
    PLAY_PAUSE = 114
    PREV_TRACK = 116
    NEXT_TRACK = 115
    SEEK_BACKWARD = 118
    SEEK_FORWARD = 117
    VOLUME_UP = 121
    VOLUME_DOWN = 122


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

