from .spotify.remote import PlaybackCommand


class PlaybackController:
    def __init__(self, spotify_remote, thread_pool_executor):
        self.executor = thread_pool_executor
        self.spotify = spotify_remote

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

