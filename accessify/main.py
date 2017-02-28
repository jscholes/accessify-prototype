import wx

import gui
import spotify


def main():
    spotify_remote = spotify.RemoteBridge(spotify.get_web_helper_port())
    event_manager = spotify.EventManager(spotify_remote)
    event_manager.start()
    app = wx.App()
    window = gui.MainWindow(spotify_remote)
    window.subscribe_to_spotify_events(event_manager)
    window.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
