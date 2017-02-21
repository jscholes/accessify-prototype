import wx

import spotify


WINDOW_TITLE = 'Accessify'
MENU_PLAYBACK = '&Playback'
LABEL_URI = 'Spoti&fy URI'
ID_PLAY_PAUSE = wx.NewId()
LABEL_PLAY_PAUSE = 'P&lay'
ID_PREVIOUS = wx.NewId()
LABEL_PREVIOUS = 'P&revious'
ID_NEXT = wx.NewId()
LABEL_NEXT = '&Next'
ID_REWIND = wx.NewId()
LABEL_REWIND = 'Re&wind'
ID_FAST_FORWARD = wx.NewId()
LABEL_FAST_FORWARD = '&Fast Forward'
ID_INCREASE_VOLUME = wx.NewId()
LABEL_INCREASE_VOLUME = '&Increase Volume'
ID_DECREASE_VOLUME = wx.NewId()
LABEL_DECREASE_VOLUME = '&Decrease Volume'


class MainWindow(wx.Frame):
    def __init__(self, spotify_remote, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, *args, **kwargs)
        self._spotify_remote = spotify_remote
        self.panel = wx.Panel(self)
        self.commands = {
            ID_PLAY_PAUSE: PlaybackCommand(LABEL_PLAY_PAUSE, spotify.CMD_PLAY_PAUSE, 'Space', True),
            ID_PREVIOUS: PlaybackCommand(LABEL_PREVIOUS, spotify.CMD_PREV_TRACK, 'Ctrl+Left', True),
            ID_NEXT: PlaybackCommand(LABEL_NEXT, spotify.CMD_NEXT_TRACK, 'Ctrl+Right', True),
            ID_REWIND: PlaybackCommand(LABEL_REWIND, spotify.CMD_SEEK_BACKWARD, 'Shift+Left', True),
            ID_FAST_FORWARD: PlaybackCommand(LABEL_FAST_FORWARD, spotify.CMD_SEEK_FORWARD, 'Shift+Right', True),
            ID_INCREASE_VOLUME: PlaybackCommand(LABEL_INCREASE_VOLUME, spotify.CMD_VOLUME_UP, 'Ctrl+Up', False),
            ID_DECREASE_VOLUME: PlaybackCommand(LABEL_DECREASE_VOLUME, spotify.CMD_VOLUME_DOWN, 'Ctrl+Down', False),
        }
        self.setup_commands(self.commands)
        self.subscribe_to_spotify_events()

    def setup_commands(self, command_dict):
        uri_label = wx.StaticText(self.panel, -1, LABEL_URI)
        self.uri_field = wx.TextCtrl(self.panel, -1, style=wx.TE_PROCESS_ENTER|wx.TE_DONTWRAP)
        self.uri_field.Bind(wx.EVT_TEXT_ENTER, self.onUriEntered)
        playback_menu = wx.Menu()
        for id, command in command_dict.items():
            if command.show_as_button:
                btn = wx.Button(self.panel, id, command.label)
                command.add_widget(btn)
                btn.Bind(wx.EVT_BUTTON, self.onPlaybackCommand)
            menu_item = playback_menu.Append(id, '{0}\t{1}'.format(command.label, command.hotkey))
            command.add_widget(menu_item)
            self.Bind(wx.EVT_MENU, self.onPlaybackCommand)
        menu_bar = wx.MenuBar()
        menu_bar.Append(playback_menu, MENU_PLAYBACK)
        self.SetMenuBar(menu_bar)

    def subscribe_to_spotify_events(self):
        event_manager = self._spotify_remote.event_manager
        event_manager.subscribe(spotify.EVENT_TRACK_CHANGE, self.onTrackChange)
        event_manager.subscribe(spotify.EVENT_PLAY, self.onPlay)
        event_manager.subscribe(spotify.EVENT_PAUSE, self.onPause)
        event_manager.start()

    def onUriEntered(self, event):
        uri = self.uri_field.GetValue()
        self.uri_field.Clear()
        if uri:
            if uri.startswith('spotify:'):
                self._spotify_remote.play_uri(uri)
            else:
                show_error(self, 'Not a valid Spotify URI.')

    def onPlaybackCommand(self, event):
        id = event.GetId()
        command = self.commands[id]
        try:
            self._spotify_remote.send_command(command.command_id)
        except spotify.SpotifyNotRunningError:
            show_error(self, 'Spotify doesn\'t seem to be running!')

    def onTrackChange(self, track):
        current_track = '{0} - {1}'.format(track.artist.name, track.name)
        wx.CallAfter(self.SetTitle, current_track)

    def onPause(self):
        wx.CallAfter(self.commands[ID_PLAY_PAUSE].update_label, 'P&lay')

    def onPlay(self):
        wx.CallAfter(self.commands[ID_PLAY_PAUSE].update_label, 'P&ause')


class PlaybackCommand:
    def __init__(self, label, command_id, hotkey, show_as_button):
        self._widgets = []
        self.label = label
        self.command_id = command_id
        self.hotkey = hotkey
        self.show_as_button = show_as_button

    def add_widget(self, widget):
        self._widgets.append(widget)

    def update_label(self, label):
        for widget in self._widgets:
            if isinstance(widget, wx.MenuItem):
                widget.SetItemLabel('{0}\t{1}'.format(label, self.hotkey))
            else:
                widget.SetLabel(label)


def show_error(parent, message):
    wx.MessageBox(message, 'Error', parent=parent, style=wx.ICON_ERROR)


if __name__ == '__main__':
    app = wx.App()
    remote = spotify.RemoteBridge(spotify.get_web_helper_port())
    window = MainWindow(remote)
    window.Show()
    app.MainLoop()
