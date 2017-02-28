from concurrent import futures
from functools import partial

import wx

import concurrency
import gui
import spotify


def main():
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


if __name__ == '__main__':
    main()
