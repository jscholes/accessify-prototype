from typing import NamedTuple, Optional


class Artist(NamedTuple):
    name: str
    uri: Optional[str] = None


class Album(NamedTuple):
    artist: Artist
    name: str
    uri: Optional[str] = None


class Track(NamedTuple):
    artist: Artist
    name: str
    uri: Optional[str] = None
    album: Optional[Album] = None
    length: Optional[int] = None
    type: str = 'normal'

