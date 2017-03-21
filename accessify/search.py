from collections import defaultdict
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class SearchController:
    def perform_new_search(self, query, search_type):
        logger.debug('Searching for {0} in {1}'.format(query, search_type))
        return sample_results[search_type]


class SearchType(Enum):
    TRACK = 'track'
    ARTIST = 'artist'
    ALBUM = 'album'
    PLAYLIST = 'playlist'
    USER = 'user'


sample_results = defaultdict(list)

sample_tracks = [
    ('Little Bird', 'Sharon Shannon', 'spotify:track:3KntH6hRCc4HY6E70xMn8F'),
    ('I\'ll Be Wise', 'Kate Rusby', 'spotify:track:5XMWL43ivHgti9I6LCqYPF'),
    ('Skibereen', 'The Wolfe Tones', 'spotify:track:7sS4BK6MdXqu3fCqPXStPb'),
    ('Song For Ireland', 'The Dubliners', 'spotify:track:26DVAZXVZ6vHgShGFW1Ebo'),
    ('The Dutchman', 'Liam Clancy', 'spotify:track:2KKQwSx8WlYLFLMi6KAoEn'),
]

sample_results.update({SearchType.TRACK: sample_tracks})

