import collections

import pyperclip

from .spotify.eventmanager import EventType
from .spotify.remote import PlaybackCommand


class PlaybackController:
    def __init__(self, spotify_remote, event_manager, thread_pool_executor):
        self.executor = thread_pool_executor
        self.playback_queue = collections.deque()
        self.spotify = spotify_remote
        event_manager.subscribe(EventType.STOP, self.advance_playback_queue)
        self.current_track = None

    def copy_current_track_uri(self):
        if self.current_track is not None:
            pyperclip.copy(self.current_track.uri)

    def queue_uri(self, uri, context=None):
        self.playback_queue.append({'uri': uri, 'context': context})

    def advance_playback_queue(self):
        try:
            item = self.playback_queue.popleft()
        except IndexError:
            return

        self.play_uri(item['uri'], item['context'])

    def clear_queue(self):
        self.playback_queue.clear()

    def play_pause(self):
        self.spotify.queue_command(PlaybackCommand.PLAY_PAUSE)

    def previous_track(self):
        self.spotify.queue_command(PlaybackCommand.PREV_TRACK)

    def next_track(self):
        self.spotify.queue_command(PlaybackCommand.NEXT_TRACK)

    def seek_backward(self):
        self.spotify.queue_command(PlaybackCommand.SEEK_BACKWARD)

    def seek_forward(self):
        self.spotify.queue_command(PlaybackCommand.SEEK_FORWARD)

    def increase_volume(self):
        self.spotify.queue_command(PlaybackCommand.VOLUME_UP)

    def decrease_volume(self):
        self.spotify.queue_command(PlaybackCommand.VOLUME_DOWN)

    def play_uri(self, uri, context=None):
        self.executor.submit(self.spotify.play_uri, uri, context)

