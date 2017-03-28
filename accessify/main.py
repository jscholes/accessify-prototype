import logging
import os
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
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    root_logger.addHandler(handler)

    logger.info('Application starting up')

    # Set up communication with Spotify
    access_token = os.environ.get('SPOTIFY_ACCESS_TOKEN')
    if access_token is None:
        print('No Spotify access token supplied.  Please set the SPOTIFY_ACCESS_TOKEN environment variable.')
        return
    spotify_remote = spotify.remote.RemoteBridge(spotify.remote.find_listening_port())
    event_manager = spotify.eventmanager.EventManager(spotify_remote)
    event_manager.start()
    playback_controller = playback.PlaybackController.start(spotify_remote, event_manager)
    search_controller = search.SearchController.start(spotify.webapi.WebAPIClient(access_token))

    # Set up the GUI
    app = wx.App()
    window = gui.main.MainWindow(playback_controller.proxy(), search_controller.proxy())
    window.SubscribeToSpotifyEvents(event_manager)
    window.Show()
    app.MainLoop()

    # Shutdown
    playback_controller.stop()
    search_controller.stop()
    logger.info('Application shutdown complete')


if __name__ == '__main__':
    main()
