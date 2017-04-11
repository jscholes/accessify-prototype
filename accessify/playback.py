import collections

import pykka
import pyperclip

from .spotify.eventmanager import EventType
from .spotify.remote import PlaybackCommand


class PlaybackController(pykka.ThreadingActor):
    use_daemon_thread = True

    def __init__(self, spotify_remote, event_manager):
        super().__init__()
        self.playback_queue = collections.deque()
        self.spotify = spotify_remote
        event_manager.subscribe(EventType.STOP, self._advance_playback_queue)
        event_manager.subscribe(EventType.TRACK_CHANGE, self._update_current_track)
        self.current_track = None

    def _advance_playback_queue(self):
        try:
            item = self.playback_queue.popleft()
        except IndexError:
            return

        self.play_item(item)

    def clear_queue(self):
        self.playback_queue.clear()

    def _update_current_track(self, track):
        self.current_track = track

    def play_item(self, item, context=None):
        self.play_uri(item.uri, context)

    def play_uri(self, uri, context=None):
        self.spotify.play_uri(uri, context)

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

