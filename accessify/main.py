from concurrent import futures
from functools import partial
import logging
import os.path

import wx

import concurrency
import gui
import spotify


logger = logging.getLogger(__package__)

log_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'accessify.log')


def main():
    # Set up logging
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(module)s: %(message)s'))
    logger.addHandler(handler)
    logger.info('Application starting up')

    # Set up concurrency
    executor = futures.ThreadPoolExecutor()
    background_worker = partial(concurrency.submit_future, executor)

    # Set up communication with Spotify
    spotify_remote = spotify.RemoteBridge(spotify.get_web_helper_port())
    event_manager = spotify.EventManager(spotify_remote)
    event_manager.start()

    # Set up the GUI
    app = wx.App()
    window = gui.MainWindow(spotify_remote, background_worker)
    window.subscribe_to_spotify_events(event_manager)
    window.Show()
    app.MainLoop()

    # Shutdown
    logger.info('Shutting down')
    executor.shutdown()


if __name__ == '__main__':
    main()
