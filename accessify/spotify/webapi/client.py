from collections import defaultdict
import os.path

import ujson as json

from accessify import structures


class WebAPIClient:
    def search(self, query, search_type):
        return sample_results[search_type]


sample_results = defaultdict(list)

sample_tracks = [
    structures.Track(structures.Artist('Sharon Shannon'), 'Little Bird', 'spotify:track:3KntH6hRCc4HY6E70xMn8F'),
    structures.Track(structures.Artist('Kate Rusby'), 'I\'ll Be Wise', 'spotify:track:5XMWL43ivHgti9I6LCqYPF'),
    structures.Track(structures.Artist('The Wolfe Tones'), 'Skibereen', 'spotify:track:7sS4BK6MdXqu3fCqPXStPb'),
    structures.Track(structures.Artist('The Dubliners'), 'Song For Ireland', 'spotify:track:26DVAZXVZ6vHgShGFW1Ebo'),
    structures.Track(structures.Artist('Liam Clancy'), 'The Dutchman', 'spotify:track:2KKQwSx8WlYLFLMi6KAoEn'),
]

sample_artists = [
    structures.Artist('Townes Van Zandt', 'spotify:artist:3ZWab2LEVkNKiBPIClTwof'),
    structures.Artist('Christy Moore', 'spotify:artist:3Ebn7mKYzD0L3DaUB1gNJZ'),
    structures.Artist('"George Jones', 'spotify:artist:2OpqcUtj10HHvGG6h9VYC5'),
]

sample_results.update({
    'track': sample_tracks,
    'artist': sample_artists,
})

