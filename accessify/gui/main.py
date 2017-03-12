import wx

from .. import spotify

from . import controls


WINDOW_TITLE = 'Accessify'
MENU_PLAYBACK = '&Playback'
LABEL_NOW_PLAYING = 'Now playing'
LABEL_URI = 'Spoti&fy URI'
LABEL_PLAY_URI = '&Play'
LABEL_QUEUE_URI = 'Add to &queue'

ID_PLAY_PAUSE = wx.NewId()
playback_commands = {
    ID_PLAY_PAUSE: {'label': 'P&lay\tCtrl+Space', 'method': 'play_pause'},
    wx.NewId(): {'label': 'P&revious\tCtrl+Left', 'method': 'previous_track'},
    wx.NewId(): {'label': '&Next\tCtrl+Right', 'method': 'next_track'},
    wx.NewId(): {'label': 'Re&wind\tShift+Left', 'method': 'seek_backward'},
    wx.NewId(): {'label': '&Fast Forward\tShift+Right', 'method': 'seek_forward'},
    wx.NewId(): {'label': '&Decrease Volume\tCtrl+Down', 'method': 'decrease_volume'},
    wx.NewId(): {'label': '&Increase Volume\tCtrl+Up', 'method': 'increase_volume'},
    wx.NewId(): {'label': 'Clear playback &Queue', 'method': 'clear_queue'},
    wx.NewId(): {'label': 'Copy current track &URI\tCtrl+C', 'method': 'copy_current_track_uri'},
}


class MainWindow(wx.Frame):
    def __init__(self, playback_controller, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, *args, **kwargs)
        self.playback = playback_controller
        self._current_track = None
        self._initialiseControls()

    def _initialiseControls(self):
        self.panel = wx.Panel(self)
        self.tabs = self._createTabs()
        self._addPages()
        self._createMenu()
        self._bindEvents()

    def         _addPages(self):
        self.tabs.AddPage(NowPlayingPage(self.tabs, self.playback), LABEL_NOW_PLAYING)

    def _createTabs(self):
        return controls.KeyboardAccessibleNotebook(self.panel, style=wx.NB_BOTTOM|wx.NB_NOPAGETHEME|wx.NB_FLAT)

    def _createMenu(self):
        playback_menu = playback_menu = wx.Menu()
        for id, command_dict in playback_commands.items():
            menu_item = playback_menu.Append(id, command_dict['label'])
        menu_bar = wx.MenuBar()
        menu_bar.Append(playback_menu, MENU_PLAYBACK)
        self.SetMenuBar(menu_bar)
        self.playback_menu = playback_menu

    def _bindEvents(self):
        self.Bind(wx.EVT_MENU, self.onPlaybackAction)
        self.Bind(wx.EVT_SHOW, self.onShow)

    def subscribe_to_spotify_events(self, event_manager):
        event_manager.subscribe(spotify.eventmanager.EventType.TRACK_CHANGE, self.onTrackChange)
        event_manager.subscribe(spotify.eventmanager.EventType.PLAY, self.onPlay)
        event_manager.subscribe(spotify.eventmanager.EventType.PAUSE, self.onPause)
        event_manager.subscribe(spotify.eventmanager.EventType.STOP, self.onStop)
        event_manager.subscribe(spotify.eventmanager.EventType.ERROR, self.onError)

    def set_current_track(self, track):
        self.playback.current_track = track
        if track is None:
            self.SetTitle(WINDOW_TITLE)
        else:
            self.SetTitle('{0} - {1}'.format(WINDOW_TITLE, format_track_display(track)))

    def onShow(self, event):
        page = self.tabs.GetCurrentPage()
        initial_focus = getattr(page, 'initial_focus', None)
        if initial_focus:
            initial_focus.SetFocus()
        event.Skip()

    def onPlaybackAction(self, event):
        id = event.GetId()
        command = playback_commands.get(id)
        if command:
            callback = getattr(self.playback, command['method'])
            callback()

    def onTrackChange(self, track):
        wx.CallAfter(self.set_current_track, track)

    def onPause(self):
        # TODO: Remove this ugly hack with CallAfter decorator
        def cb():
            mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
            mi.SetItemLabel('P&lay\tCtrl+Space')

        wx.CallAfter(cb)

    def onPlay(self):
        # TODO: Remove this ugly hack with CallAfter decorator
        def cb():
            mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
            mi.SetItemLabel('P&ause\tCtrl+Space')

        wx.CallAfter(cb)

    def onStop(self):
        wx.CallAfter(self.onPause)
        wx.CallAfter(self.set_current_track, None)

    def onError(self, exception):
        show_error(self, exception.error_description)


class TabsPage(wx.Panel):
    def __init__(self, parent, playback_controller, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.playback = playback_controller
        self._initialiseControls()


class NowPlayingPage(TabsPage):
    def _initialiseControls(self):
        uri_label = wx.StaticText(self, -1, LABEL_URI)
        self.uri_field = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER|wx.TE_DONTWRAP)
        self.uri_field.Bind(wx.EVT_TEXT_ENTER, self.onUriEntered)
        self.initial_focus = self.uri_field

        self._addButtons()

    def _addButtons(self):
        play_button = wx.Button(self, wx.ID_ANY, LABEL_PLAY_URI)
        play_button.Bind(wx.EVT_BUTTON, self.onPlay)
        queue_button = wx.Button(self, wx.ID_ANY, LABEL_QUEUE_URI)
        queue_button.Bind(wx.EVT_BUTTON, self.onQueue)

    def onUriEntered(self, event):
        uri = self.uri_field.GetValue()
        self.uri_field.Clear()
        if uri:
            if uri.startswith('spotify:'):
                self.playback.play_uri( uri)
            else:
                show_error(self, 'Not a valid Spotify URI.')

    def onPlay(self, event):
        self.onUriEntered(None)
        self.uri_field.SetFocus()

    def onQueue(self, event):
        self.playback.queue_uri(self.uri_field.GetValue())
        self.uri_field.Clear()
        self.uri_field.SetFocus()



def show_error(parent, message):
    wx.CallAfter(wx.MessageBox, message, 'Error', parent=parent, style=wx.ICON_ERROR)


def format_track_display(track):
    return '{0} - {1}'.format(track.artist.name, track.name).replace('&', 'and')

