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


class ItemCollection:
    def __init__(self, items, total):
        self._items = items
        self.total = total

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

