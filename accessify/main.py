import logging
import os.path

from appdirs import user_config_dir
import ujson as json
import wx

from . import constants
from . import gui
from . import library
from . import playback
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

    # Load the config
    config_path = os.path.join(config_directory, 'config.json')
    config = load_config(config_path)

    # Set up communication with Spotify
    access_token = config.get('spotify_access_token')
    if not access_token:
        print('No Spotify access token supplied.  Please provide an access token in the config file located at {0}'.format(config_path))
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
    save_config(config, config_path)
    logger.info('Application shutdown complete')


def load_config(path):
    logger.info('Attempting to load config from {0}'.format(path))
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, ValueError):
        logger.info('Valid existing config not found, creating default')
        return default_config

    for key in default_config.keys():
        if key not in config:
            config.update({key: default_config[key]})
    return config


def save_config(config_dict, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=4)
    logger.info('Config saved to {0}'.format(path))


default_config = {
    'spotify_access_token': '',
}


if __name__ == '__main__':
    main()
