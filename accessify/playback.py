import collections
import logging

import pykka
import pyperclip

from accessify.signalling import Signalman
from accessify import spotify
from accessify.spotify.eventmanager import EventType, PlaybackState
from accessify.spotify import exceptions
from accessify.spotify.remote import PlaybackCommand


logger = logging.getLogger(__name__)


class PlaybackController(pykka.ThreadingActor):
    use_daemon_thread = True

    def __init__(self, signalman, config):
        super().__init__()
        self._signalman = signalman
        self.config = config
        self.playback_queue = collections.deque()
        self.current_track = None
        self._connected = None

    def connect_to_spotify(self):
        try:
            self.spotify = spotify.remote.RemoteBridge(spotify.remote.find_listening_port())
        except spotify.remote.exceptions.SpotifyNotRunningError as e:
            self._signalman.spotify_not_running.send()
            return

        event_manager = spotify.eventmanager.EventManager(self.spotify, self.config.get('spotify_polling_interval'))
        self._connect_spotify_events(event_manager)
        event_manager.start()

    def _connect_spotify_events(self, event_manager):
        event_manager.subscribe(EventType.PLAY, self.on_play)
        event_manager.subscribe(EventType.PAUSE, self.on_pause)
        event_manager.subscribe(EventType.STOP, self.on_stop)
        event_manager.subscribe(EventType.TRACK_CHANGE, self.on_track_change)
        event_manager.subscribe(EventType.ERROR, self.on_error)

    def on_play(self, track):
        if not self._connected:
            self._connected = True
            self._signalman.connection_established.send(None)
        self._signalman.state_changed.send(PlaybackState.PLAYING, track=self.current_track)

    def on_pause(self):
        if not self._connected:
            self._connected = True
            self._signalman.connection_established.send(None)
        self._signalman.state_changed.send(PlaybackState.PAUSED, track=self.current_track)

    def on_stop(self):
        next_item = self._advance_playback_queue()
        if next_item is not None:
            self.play_item(next_item)
        else:
            if not self._connected:
                self._connected = True
                self._signalman.connection_established.send(None)
            self._signalman.state_changed.send(PlaybackState.STOPPED, track=self.current_track)

    def on_track_change(self, new_track):
        if not self._connected:
            self._connected = True
            self._signalman.connection_established.send(None)
        self.current_track = new_track
        self._signalman.track_changed.send(new_track)

    def on_error(self, exception):
        if isinstance(exception, exceptions.ContentPlaybackError):
            self._signalman.unplayable_content.send(exception.uri)
        elif isinstance(exception, exceptions.MetadataNotReadyError):
            self.on_track_change(None)
        else:
            self._connected = False
            self._signalman.error.send(exception)

    def _advance_playback_queue(self):
        try:
            return self.playback_queue.popleft()
        except IndexError:
            return None

    def clear_queue(self):
        self.playback_queue.clear()

    def play_item(self, item, context=None):
        self.play_uri(item.uri, context)

    def play_uri(self, uri, context=None):
        try:
            self.spotify.play_uri(uri, context)
        except exceptions.SpotifyError as e:
            logger.error('Error while trying to play URI {0} with context {1}'.format(uri, context), exc_info=True)
            self.on_error(e_)

    def queue_item(self, item, context=None):
        self.playback_queue.append(item)

    def copy_current_track_uri(self):
        if self.current_track is not None:
            self.copy_item_uri(self.current_track)

    def copy_item_uri(self, item):
        pyperclip.copy(item.uri)

    def play_pause(self):
        self.spotify.send_command(PlaybackCommand.PLAY_PAUSE)

    def previous_track(self):
        self.spotify.send_command(PlaybackCommand.PREV_TRACK)

    def next_track(self):
        self.spotify.send_command(PlaybackCommand.NEXT_TRACK)

    def seek_backward(self):
        self.spotify.send_command(PlaybackCommand.SEEK_BACKWARD)

    def seek_forward(self):
        self.spotify.send_command(PlaybackCommand.SEEK_FORWARD)

    def increase_volume(self):
        self.spotify.send_command(PlaybackCommand.VOLUME_UP)

    def decrease_volume(self):
        self.spotify.send_command(PlaybackCommand.VOLUME_DOWN)


class PlaybackSignalman(Signalman):
    signals = ('state_changed', 'track_changed', 'unplayable_content', 'connection_established', 'spotify_not_running', 'error')

