import logging
import os
import os.path

from appdirs import user_config_dir
import tolk
import ujson as json
import wx

from accessify import constants

try:
    from accessify import credentials
    has_credentials = True
except ImportError:
    has_credentials = False

from accessify import gui
from accessify import library
from accessify import playback
from accessify import spotify


logger = logging.getLogger(__package__)


def main():
    app = wx.App()
    instance_checker = wx.SingleInstanceChecker()
    if instance_checker.IsAnotherRunning():
        # TODO: Focus the existing instance instead
        gui.utils.show_error(None, 'Accessify is already running.')
        return

    config_directory = user_config_dir(appname=constants.APP_NAME, appauthor=False, roaming=True)
    try:
        os.makedirs(config_directory)
    except FileExistsError:
        pass

    log_filename = '{0}.log'.format(constants.APP_NAME.lower())
    log_path = os.path.join(config_directory, log_filename)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    root_logger.addHandler(handler)

    logger.info('Version: {0}'.format(constants.APP_VERSION))

    config_path = os.path.join(config_directory, 'config.json')
    config = load_config(config_path)

    if has_credentials:
        client_id = credentials.client_id
        client_secret = credentials.client_secret
    else:
        client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')

    if not client_id or not client_secret:
        print('No Spotify credentials provided.  Please either set the environment variables SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET or create a credentials module with client_id and client_secret variables.')
        return

    access_token = config.get('spotify_access_token')
    refresh_token = config.get('spotify_refresh_token')
    if not access_token or not refresh_token:
        print('You\'re missing either a Spotify access or refresh token in your config file.  Please provide these in the config file located at {0}'.format(config_path))
        return

    try:
        tolk.load()
    except Exception:
        pass

    auth_agent = spotify.webapi.authorisation.AuthorisationAgent(client_id, client_secret, access_token, refresh_token)
    spotify_api_client = spotify.webapi.WebAPIClient(auth_agent)

    # TODO: Move this to a more appropriate place
    try:
        spotify_remote = spotify.remote.RemoteBridge(spotify.remote.find_listening_port())
    except spotify.remote.exceptions.SpotifyNotRunningError:
        print('Spotify doesn\'t seem to be running.')
        return

    event_manager = spotify.eventmanager.EventManager(spotify_remote)
    psignalman = playback.PlaybackSignalman()
    playback_controller = playback.PlaybackController.start(psignalman, spotify_remote, event_manager)
    playback_proxy = playback_controller.proxy()

    library_controller = library.LibraryController.start(config, spotify_api_client)
    library_proxy = library_controller.proxy()

    window = gui.main.MainWindow(playback_proxy, library_proxy)

    psignalman.state_change.connect(window.onPlaybackStateChange)
    psignalman.track_change.connect(window.onTrackChange)
    psignalman.error.connect(window.onSpotifyError)

    playback_proxy.connect_to_spotify()
    library_proxy.log_in()
    event_manager.start()
    app.MainLoop()

    # Shutdown
    playback_controller.stop()
    library_controller.stop()
    save_config(config, config_path)
    tolk.unload()
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
    'spotify_refresh_token': '',
}


if __name__ == '__main__':
    main()
