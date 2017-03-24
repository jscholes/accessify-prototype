from concurrent import futures
import logging
import os.path

import wx

from . import gui
from . import playback
from . import search
from . import spotify


logger = logging.getLogger(__package__)

log_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'accessify.log')


def main():
    # Set up logging
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    logger.addHandler(handler)
    logger.info('Application starting up')

    # Set up concurrency
    executor = futures.ThreadPoolExecutor()

    # Set up communication with Spotify
    spotify_remote = spotify.remote.RemoteBridge(spotify.remote.find_listening_port())
    event_manager = spotify.eventmanager.EventManager(spotify_remote)
    event_manager.start()
    playback_controller = playback.PlaybackController(spotify_remote, event_manager, executor)
    search_controller = search.SearchController(spotify.webapi.WebAPIClient())

    # Set up the GUI
    app = wx.App()
    window = gui.main.MainWindow(playback_controller, search_controller)
    window.SubscribeToSpotifyEvents(event_manager)
    window.Show()
    app.MainLoop()

    # Shutdown
    logger.info('Shutting down')
    executor.shutdown()


if __name__ == '__main__':
    main()
