from collections import namedtuple


Track = namedtuple('Track', ['artist', 'album', 'name', 'length', 'type', 'uri'])
Artist = namedtuple('Artist', ['name', 'uri'])
Album = namedtuple('Album', ['name', 'uri'])
PlaybackStatus = namedtuple('PlaybackStatus', ['playing', 'position', 'volume', 'repeat', 'shuffle'])
SpotifyStatus = namedtuple('SpotifyStatus', ['client_version', 'running'])
