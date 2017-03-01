import wx

from .. import spotify


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
    def __init__(self, spotify_remote, background_worker, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, *args, **kwargs)
        self._spotify_remote = spotify_remote
        self.background_worker = background_worker
        self._current_track = None
        self.panel = wx.Panel(self)
        self.commands = {
            ID_PLAY_PAUSE: PlaybackCommand(LABEL_PLAY_PAUSE, spotify.remote.PlaybackCommand.PLAY_PAUSE, 'Ctrl+Space', True),
            ID_PREVIOUS: PlaybackCommand(LABEL_PREVIOUS, spotify.remote.PlaybackCommand.PREV_TRACK, 'Ctrl+Left', True),
            ID_NEXT: PlaybackCommand(LABEL_NEXT, spotify.remote.PlaybackCommand.NEXT_TRACK, 'Ctrl+Right', True),
            ID_REWIND: PlaybackCommand(LABEL_REWIND, spotify.remote.PlaybackCommand.SEEK_BACKWARD, 'Shift+Left', True),
            ID_FAST_FORWARD: PlaybackCommand(LABEL_FAST_FORWARD, spotify.remote.PlaybackCommand.SEEK_FORWARD, 'Shift+Right', True),
            ID_INCREASE_VOLUME: PlaybackCommand(LABEL_INCREASE_VOLUME, spotify.remote.PlaybackCommand.VOLUME_UP, 'Ctrl+Up', False),
            ID_DECREASE_VOLUME: PlaybackCommand(LABEL_DECREASE_VOLUME, spotify.remote.PlaybackCommand.VOLUME_DOWN, 'Ctrl+Down', False),
        }
        self.setup_commands(self.commands)

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

    def subscribe_to_spotify_events(self, event_manager):
        event_manager.subscribe(spotify.eventmanager.EventType.TRACK_CHANGE, self.onTrackChange)
        event_manager.subscribe(spotify.eventmanager.EventType.PLAY, self.onPlay)
        event_manager.subscribe(spotify.eventmanager.EventType.PAUSE, self.onPause)
        event_manager.subscribe(spotify.eventmanager.EventType.STOP, self.onStop)
        event_manager.subscribe(spotify.eventmanager.EventType.ERROR, self.onError)

    def set_current_track(self, track):
        self._current_track = track
        if self._current_track is None:
            self.SetTitle(WINDOW_TITLE)
        else:
            self.SetTitle('{0} - {1}'.format(WINDOW_TITLE, format_track_display(self._current_track)))

    def onUriEntered(self, event):
        uri = self.uri_field.GetValue()
        self.uri_field.Clear()
        if uri:
            if uri.startswith('spotify:'):
                self.background_worker(self._spotify_remote.play_uri, uri, error_callback=self.onError)
            else:
                show_error(self, 'Not a valid Spotify URI.')

    def onPlaybackCommand(self, event):
        id = event.GetId()
        command = self.commands[id]
        self._spotify_remote.send_command(command.command_id)

    def onTrackChange(self, track):
        wx.CallAfter(self.set_current_track, track)

    def onPause(self):
        wx.CallAfter(self.commands[ID_PLAY_PAUSE].update_label, 'P&lay')

    def onPlay(self):
        wx.CallAfter(self.commands[ID_PLAY_PAUSE].update_label, 'P&ause')

    def onStop(self):
        wx.CallAfter(self.onPause)
        wx.CallAfter(self.set_current_track, None)

    def onError(self, exception):
        show_error(self, exception.error_description)


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
    wx.CallAfter(wx.MessageBox, message, 'Error', parent=parent, style=wx.ICON_ERROR)


def format_track_display(track):
    return '{0} - {1}'.format(track.artist.name, track.name).replace('&', 'and')
