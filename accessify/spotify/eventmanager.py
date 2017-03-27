from collections import defaultdict
from enum import Enum
import logging
import queue
import threading

from ..utils.concurrency import consume_queue
from .. import structures

from . import exceptions


logger = logging.getLogger(__name__)


class EventManager(threading.Thread):
    def __init__(self, remote_bridge, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDaemon(True)

        self._remote_bridge = remote_bridge
        self._event_queue = queue.Queue()
        self._callbacks = defaultdict(list)

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
                    status = self._remote_bridge.get_status()
                else:
                    status = self._remote_bridge.get_status(return_after=60)
                self._event_queue.put(status)
                return_immediately = False
            except exceptions.MetadataNotReadyError:
                return_immediately = True
                continue
            except exceptions.SpotifyRemoteError as e:
                self._event_queue.put(e)

    def _process_item(self, item):
        if isinstance(item, exceptions.SpotifyRemoteError):
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
    artist = structures.Artist(name=artist_res['name'], uri=artist_res['uri'])
    album = structures.Album(artists=[artist], name=album_res['name'], uri=album_res['uri'])
    track = structures.Track(artists=[artist], name=track_res['name'], uri=track_res['uri'], album=album, length=track_dict['length'], type=track_dict['track_type'])
    return track


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

