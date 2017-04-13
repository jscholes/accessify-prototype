class SpotifyError(Exception):
    pass


class SpotifyNotRunningError(SpotifyError):
    """Raised when the HWND of the Spotify main window cannot be found."""


class SpotifyRemoteError(SpotifyError):
    """Raised when the Spotify remote service returns an error code."""

    def __init__(self, error_code, error_description, *args, **kwargs):
        self.error_code = error_code
        self.error_description = error_description


class MetadataNotReadyError(SpotifyError):
    """Raised when Spotify has started playing a track, but the track resource hasn't been fully populated with metadata yet."""


class SpotifyConnectionError(SpotifyError):
    pass

