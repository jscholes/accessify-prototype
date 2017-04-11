class SpotifyNotRunningError(Exception):
    """Raised when the HWND of the Spotify main window cannot be found."""


class SpotifyRemoteError(Exception):
    """Raised when the Spotify remote service returns an error code."""

    def __init__(self, error_code, error_description, *args, **kwargs):
        self.error_code = error_code
        self.error_description = error_description


class MetadataNotReadyError(Exception):
    """Raised when Spotify has started playing a track, but the track resource hasn't been fully populated with metadata yet."""


class SpotifyConnectionError(Exception):
    pass

