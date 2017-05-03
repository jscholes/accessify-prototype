from datetime import datetime
import logging
import os
import os.path
import platform
import sys

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
from accessify import ipc
from accessify import library
from accessify import playback
from accessify import spotify


logger = logging.getLogger(__package__)

LOG_RECORD_FORMAT = '%(levelname)s - %(asctime)s:%(msecs)d:\n%(name)s: %(message)s'
LOG_DATE_TIME_FORMAT = '%d-%m-%Y @ %H:%M:%S'
LOG_FILE_DATE_TIME_FORMAT = '%Y_%m_%d-%H_%M_%S'


def main():
    config_directory = user_config_dir(appname=constants.APP_NAME, appauthor=False, roaming=True)
    hwnd_file = os.path.join(config_directory, '{0}.hwnd'.format(constants.APP_NAME))

    app = wx.App()
    instance_checker = wx.SingleInstanceChecker()
    if instance_checker.IsAnotherRunning():
        hwnd = ipc.get_existing_hwnd(hwnd_file)
        if hwnd:
            ipc.focus_window(hwnd)
        else:
            gui.utils.show_error(None, 'Accessify is already running.')
        return

    config_directory = user_config_dir(appname=constants.APP_NAME, appauthor=False, roaming=True)
    log_directory = os.path.join(config_directory, 'logs')
    try:
        os.makedirs(log_directory)
    except FileExistsError:
        pass

    log_filename = '{0}.{1}.log'.format(constants.APP_NAME.lower(), datetime.utcnow().strftime(LOG_FILE_DATE_TIME_FORMAT))
    log_path = os.path.join(log_directory, log_filename)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter(LOG_RECORD_FORMAT, LOG_DATE_TIME_FORMAT))
    root_logger.addHandler(handler)

    log_startup_info()

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
        logger.error('No Spotify credentials provided.')
        return

    try:
        tolk.load()
    except Exception:
        pass

    auth_agent = spotify.webapi.authorisation.AuthorisationAgent(client_id, client_secret)
    spotify_api_client = spotify.webapi.WebAPIClient(auth_agent)

    psignalman = playback.PlaybackSignalman()
    playback_controller = playback.PlaybackController.start(psignalman, config)
    playback_proxy = playback_controller.proxy()

    lsignalman = library.LibrarySignalman()
    library_controller = library.LibraryController.start(lsignalman, config, spotify_api_client)
    library_proxy = library_controller.proxy()

    window = gui.main.MainWindow(playback_proxy, library_proxy)
    ipc.save_hwnd(window.GetHandle(), hwnd_file)

    psignalman.state_changed.connect(window.onPlaybackStateChange)
    psignalman.track_changed.connect(window.onTrackChange)
    psignalman.unplayable_content.connect(window.onUnplayableContent)
    psignalman.connection_established.connect(window.onSpotifyConnectionEstablished)
    psignalman.spotify_not_running.connect(window.onSpotifyNotRunning)
    psignalman.error.connect(window.onSpotifyError)

    lsignalman.authorisation_required.connect(window.onAuthorisationRequired)
    lsignalman.authorisation_completed.connect(window.onAuthorisationCompleted)
    # lsignalman.authorisation_error.connect(window.onAuthorisationError)

    playback_proxy.connect_to_spotify()
    library_proxy.log_in()
    app.MainLoop()

    # Shutdown
    playback_controller.stop()
    library_controller.stop()
    save_config(config, config_path)
    tolk.unload()
    logger.info('Application shutdown complete')


def log_startup_info():
    logger.info('Version: {0}'.format(constants.APP_VERSION))

    # Windows info
    release, version, service_pack, processor_type = platform.win32_ver()
    uname = platform.uname()
    logger.info('OS: Windows {0} {1} ({2}) running on {3}'.format(release, service_pack, version, uname.machine))

    # Python info
    logger.info('Python {0}'.format(sys.version))


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
    'spotify_polling_interval': 60,
}


if __name__ == '__main__':
    main()

