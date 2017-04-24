import collections
import logging

import pykka
import pyperclip

from accessify.signalling import Signalman
from accessify.spotify.eventmanager import EventType, PlaybackState
from accessify.spotify import exceptions
from accessify.spotify.remote import PlaybackCommand


logger = logging.getLogger(__name__)


class PlaybackController(pykka.ThreadingActor):
    use_daemon_thread = True

    def __init__(self, signalman, spotify_remote, event_manager):
        super().__init__()
        self._signalman = signalman
        self.spotify = spotify_remote
        self._event_manager = event_manager

        self.playback_queue = collections.deque()
        self.current_track = None
        self._error_callback = None

    def connect_to_spotify(self):
        self._event_manager.subscribe(EventType.PLAY, self.on_play)
        self._event_manager.subscribe(EventType.PAUSE, self.on_pause)
        self._event_manager.subscribe(EventType.STOP, self.on_stop)
        self._event_manager.subscribe(EventType.TRACK_CHANGE, self.on_track_change)
        self._event_manager.subscribe(EventType.ERROR, self.on_error)

    def on_play(self, track):
        self._signalman.state_change.send(PlaybackState.PLAYING, track=self.current_track)

    def on_pause(self):
        self._signalman.state_change.send(PlaybackState.PAUSED, track=self.current_track)

    def on_stop(self):
        next_item = self._advance_playback_queue()
        if next_item is not None:
            self.play_item(next_item)
        else:
            self._signalman.state_change.send(PlaybackState.STOPPED, track=self.current_track)

    def on_track_change(self, new_track):
        self.current_track = new_track
        self._signalman.track_change.send(new_track)

    def on_error(self, exc):
        self._signalman.error.send(exc)

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
            if self._error_callback is not None:
                self._error_callback(e)

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
    signals = ('state_change', 'track_change', 'error')

