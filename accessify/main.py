import logging
import os
import os.path

from appdirs import user_config_dir
import wx

from . import constants
from . import gui
from . import playback
from . import library
from . import spotify


logger = logging.getLogger(__package__)


def main():
    config_directory = user_config_dir(appname=constants.APP_NAME, appauthor=False, roaming=True)
    try:
        os.makedirs(config_directory)
    except FileExistsError:
        pass

    # Set up logging
    log_filename = '{0}.log'.format(constants.APP_NAME.lower())
    log_path = os.path.join(config_directory, log_filename)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    root_logger.addHandler(handler)

    logger.info('{0} v{1}'.format(constants.APP_NAME, constants.APP_VERSION))

    # Set up communication with Spotify
    access_token = os.environ.get('SPOTIFY_ACCESS_TOKEN')
    if access_token is None:
        print('No Spotify access token supplied.  Please set the SPOTIFY_ACCESS_TOKEN environment variable.')
        return
    spotify_remote = spotify.remote.RemoteBridge(spotify.remote.find_listening_port())
    event_manager = spotify.eventmanager.EventManager(spotify_remote)
    event_manager.start()
    playback_controller = playback.PlaybackController.start(spotify_remote, event_manager)
    library_controller = library.LibraryController.start(spotify.webapi.WebAPIClient(access_token))

    # Set up the GUI
    app = wx.App()
    window = gui.main.MainWindow(playback_controller.proxy(), library_controller.proxy())
    window.SubscribeToSpotifyEvents(event_manager)
    window.Show()
    app.MainLoop()

    # Shutdown
    playback_controller.stop()
    library_controller.stop()
    logger.info('Application shutdown complete')


if __name__ == '__main__':
    main()
