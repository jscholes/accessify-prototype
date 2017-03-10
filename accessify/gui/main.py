import wx

from .. import spotify

from .actions import GUIAction
from . import controls


WINDOW_TITLE = 'Accessify'
MENU_PLAYBACK = '&Playback'
LABEL_NOW_PLAYING = 'Now playing'
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
ID_DECREASE_VOLUME = wx.NewId()
LABEL_DECREASE_VOLUME = '&Decrease Volume'
ID_INCREASE_VOLUME = wx.NewId()
LABEL_INCREASE_VOLUME = '&Increase Volume'


class MainWindow(wx.Frame):
    def __init__(self, playback_controller, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, *args, **kwargs)
        self.playback = playback_controller
        self._current_track = None
        self.actions = {
            ID_PLAY_PAUSE: GUIAction(LABEL_PLAY_PAUSE, self.playback.play_pause, 'Ctrl+Space'),
            ID_PREVIOUS: GUIAction(LABEL_PREVIOUS, self.playback.previous_track, 'Ctrl+Left'),
            ID_NEXT: GUIAction(LABEL_NEXT, self.playback.next_track, 'Ctrl+Right'),
            ID_REWIND: GUIAction(LABEL_REWIND, self.playback.seek_backward, 'Shift+Left'),
            ID_FAST_FORWARD: GUIAction(LABEL_FAST_FORWARD, self.playback.seek_forward, 'Shift+Right'),
            ID_DECREASE_VOLUME: GUIAction(LABEL_DECREASE_VOLUME, self.playback.decrease_volume, 'Ctrl+Down'),
            ID_INCREASE_VOLUME: GUIAction(LABEL_INCREASE_VOLUME, self.playback.increase_volume, 'Ctrl+Up'),
        }
        self.panel = wx.Panel(self)
        self.tabs = controls.KeyboardAccessibleNotebook(self.panel, style=wx.NB_BOTTOM|wx.NB_NOPAGETHEME|wx.NB_FLAT)
        self.now_playing_panel = NowPlayingPanel(self.tabs, self)
        self.InitialiseActions(self.actions)
        self.now_playing_panel.InitialiseActions(self.actions)
        self.tabs.AddPage(self.now_playing_panel, LABEL_NOW_PLAYING)
        self.Bind(wx.EVT_SHOW, self.onShow)

    def InitialiseActions(self, action_dict):
        playback_menu = wx.Menu()
        for id, action in action_dict.items():
            menu_item = playback_menu.Append(id, '{0}\t{1}'.format(action.label, action.hotkey))
            action.attach_widget(menu_item)
        self.Bind(wx.EVT_MENU, self.onPlaybackAction)
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

    def onShow(self, event):
        page = self.tabs.GetCurrentPage()
        initial_focus = getattr(page, 'initial_focus', None)
        if initial_focus:
            initial_focus.SetFocus()
        event.Skip()

    def onUriEntered(self, event):
        uri = self.now_playing_panel.uri_field.GetValue()
        self.now_playing_panel.uri_field.Clear()
        if uri:
            if uri.startswith('spotify:'):
                self.playback.play_uri( uri)
            else:
                show_error(self, 'Not a valid Spotify URI.')

    def onPlaybackAction(self, event):
        id = event.GetId()
        action = self.actions[id]
        action.callback()

    def onTrackChange(self, track):
        wx.CallAfter(self.set_current_track, track)

    def onPause(self):
        wx.CallAfter(self.actions[ID_PLAY_PAUSE].set_label, 'P&lay')

    def onPlay(self):
        wx.CallAfter(self.actions[ID_PLAY_PAUSE].set_label, 'P&ause')

    def onStop(self):
        wx.CallAfter(self.onPause)
        wx.CallAfter(self.set_current_track, None)

    def onError(self, exception):
        show_error(self, exception.error_description)


class NowPlayingPanel(wx.Panel):
    def __init__(self, parent, main_window, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.main_window = main_window

    def InitialiseActions(self, action_dict):
        uri_label = wx.StaticText(self, -1, LABEL_URI)
        self.uri_field = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER|wx.TE_DONTWRAP)
        self.uri_field.Bind(wx.EVT_TEXT_ENTER, self.main_window.onUriEntered)
        self.initial_focus = self.uri_field
        for id, action in action_dict.items():
            btn = wx.Button(self, id, action.label)
            action.attach_widget(btn)
            btn.Bind(wx.EVT_BUTTON, self.main_window.onPlaybackAction)


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

