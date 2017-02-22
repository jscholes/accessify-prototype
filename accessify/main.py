import wx

import gui
import spotify


def main():
    app = wx.App()
    remote = spotify.RemoteBridge(spotify.get_web_helper_port())
    window = gui.MainWindow(remote)
    window.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
