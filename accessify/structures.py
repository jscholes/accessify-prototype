from typing import Iterable, NamedTuple, Optional


class Artist(NamedTuple):
    name: str
    uri: Optional[str] = None


class Album(NamedTuple):
    artists: Iterable[Artist]
    name: str
    uri: Optional[str] = None


class Track(NamedTuple):
    artists: Iterable[Artist]
    name: str
    uri: Optional[str] = None
    album: Optional[Album] = None
    length: Optional[int] = None
    type: str = 'normal'


class Playlist(NamedTuple):
    name: str
    total_tracks: int
    uri: Optional[str] = None

