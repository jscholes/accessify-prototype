from collections import namedtuple
import threading
import time

import wx

import spotify


WINDOW_TITLE = 'Accessify'
MENU_PLAYBACK = '&Playback'
LABEL_PLAY_PAUSE = 'P&lay/Pause'
LABEL_PREVIOUS = 'P&revious'
LABEL_NEXT = '&Next'
LABEL_REWIND = 'Re&wind'
LABEL_FAST_FORWARD = '&Fast Forward'
LABEL_INCREASE_VOLUME = '&Increase Volume'
LABEL_DECREASE_VOLUME = '&Decrease Volume'

PlaybackCommand = namedtuple('PlaybackCommand', ['label', 'func', 'hotkey', 'show_as_button'])


class MainWindow(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, *args, **kwargs)
        self.panel = wx.Panel(self)
        self.commands = {
            wx.NewId(): PlaybackCommand(LABEL_PLAY_PAUSE, spotify.play_pause, 'Space', True),
            wx.NewId(): PlaybackCommand(LABEL_PREVIOUS, spotify.previous_track, 'Ctrl+Left', True),
            wx.NewId(): PlaybackCommand(LABEL_NEXT, spotify.next_track, 'Ctrl+Right', True),
            wx.NewId(): PlaybackCommand(LABEL_REWIND, spotify.seek_backwards, 'Shift+Left', True),
            wx.NewId(): PlaybackCommand(LABEL_FAST_FORWARD, spotify.seek_forwards, 'Shift+Right', True),
            wx.NewId(): PlaybackCommand(LABEL_INCREASE_VOLUME, spotify.increase_volume, 'Ctrl+Up', False),
            wx.NewId(): PlaybackCommand(LABEL_DECREASE_VOLUME, spotify.decrease_volume, 'Ctrl+Down', False),
        }
        self.setup_commands(self.commands)

    def setup_commands(self, command_dict):
        playback_menu = wx.Menu()
        for id, command in command_dict.items():
            if command.show_as_button:
                btn = wx.Button(self.panel, id, command.label)
                btn.Bind(wx.EVT_BUTTON, self.onPlaybackCommand)
            playback_menu.Append(id, '{0}\t{1}'.format(command.label, command.hotkey))
            self.Bind(wx.EVT_MENU, self.onPlaybackCommand)
        menu_bar = wx.MenuBar()
        menu_bar.Append(playback_menu, MENU_PLAYBACK)
        self.SetMenuBar(menu_bar)

    def onPlaybackCommand(self, event):
        id = event.GetId()
        command = self.commands[id]
        try:
            command.func()
        except spotify.SpotifyNotRunningError:
            show_error(self, 'Spotify doesn\'t seem to be running!')

    def onSpotifyStatus(self, status_dict):
        track_node = status_dict['track']
        current_track = '{0} - {1}'.format(track_node['artist_resource']['name'], track_node['track_resource']['name'])
        wx.CallAfter(self.SetTitle, '{0}: {1}'.format(WINDOW_TITLE, current_track))


def connect_to_spotify(status_callback):
    remote = spotify.RemoteBridge(spotify.get_web_helper_port())
    while True:
        status = remote.get_status()
        status_callback(status)
        time.sleep(0.1)


def show_error(parent, message):
    wx.MessageBox(message, 'Error', parent=parent, style=wx.ICON_ERROR)


if __name__ == '__main__':
    app = wx.App()
    window = MainWindow()
    threading.Thread(daemon=True, target=connect_to_spotify, args=(window.onSpotifyStatus,)).start()
    window.Show()
    app.MainLoop()
