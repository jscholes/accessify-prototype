from functional import seq
import wx

from .. import spotify
from .. import structures

from . import nowplaying
from . import search
from . import speech
from . import utils
from . import widgets


WINDOW_TITLE = 'Accessify'
MENU_PLAYBACK = '&Playback'
MSG_LOADING = 'Loading...'

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
    def __init__(self, playback_controller, library_controller, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, size=(900, 900), *args, **kwargs)
        speech.speak(MSG_LOADING)
        self.playback = playback_controller
        self.library = library_controller
        self.InitialiseControls()
        self.Centre()

        self._connected_to_spotify = False

    def InitialiseControls(self):
        self.panel = wx.Panel(self)
        self.tabs = self._createTabs()
        self._addPages()
        self._createMenus()
        self._bindEvents()

    def _createTabs(self):
        return widgets.KeyboardAccessibleNotebook(self.panel, style=wx.NB_BOTTOM|wx.NB_NOPAGETHEME|wx.NB_FLAT)

    def         _addPages(self):
        self.tabs.AddPage(search.SearchPage(self.tabs, self.playback, self.library), search.LABEL_SEARCH)
        self.tabs.AddPage(nowplaying.NowPlayingPage(self.tabs, self.playback), nowplaying.LABEL_NOW_PLAYING)

    def _createMenus(self):
        playback_menu = wx.Menu()
        for id, command_dict in playback_commands.items():
            menu_item = playback_menu.Append(id, command_dict['label'])
        menu_bar = wx.MenuBar()
        menu_bar.Append(playback_menu, MENU_PLAYBACK)
        self.SetMenuBar(menu_bar)
        self.playback_menu = playback_menu

    def _bindEvents(self):
        self.Bind(wx.EVT_MENU, self.onPlaybackCommand)
        self.Bind(wx.EVT_SHOW, self.onShow)

    def SubscribeToSpotifyEvents(self, event_manager):
        event_manager.subscribe(spotify.eventmanager.EventType.TRACK_CHANGE, self.onTrackChange)
        event_manager.subscribe(spotify.eventmanager.EventType.PLAY, self.onPlay)
        event_manager.subscribe(spotify.eventmanager.EventType.PAUSE, self.onPause)
        event_manager.subscribe(spotify.eventmanager.EventType.ERROR, self.onSpotifyError)

    def UpdateTrackDisplay(self, track):
        if track is None:
            self.SetTitle(WINDOW_TITLE)
        else:
            self.SetTitle('{0} - {1}'.format(WINDOW_TITLE, format_track_display(track)))
        if not self._connected_to_spotify:
            self._connected_to_spotify = True
            self.Show()

    def onShow(self, event):
        page = self.tabs.GetCurrentPage()
        initial_focus = getattr(page, 'initial_focus', None)
        if initial_focus:
            initial_focus.SetFocus()
        event.Skip()

    def onPlaybackCommand(self, event):
        id = event.GetId()
        command = playback_commands.get(id)
        if command:
            getattr(self.playback, command['method'])()

    def onTrackChange(self, track):
        wx.CallAfter(self.UpdateTrackDisplay, track)

    def onPause(self):
        # TODO: Remove this ugly hack with CallAfter decorator
        def cb():
            mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
            mi.SetItemLabel('P&lay\tCtrl+Space')
            self._connected_to_spotify = True

        wx.CallAfter(cb)

    def onPlay(self):
        # TODO: Remove this ugly hack with CallAfter decorator
        def cb():
            mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
            mi.SetItemLabel('P&ause\tCtrl+Space')
            self.UpdateTrackDisplay(None)
            self._connected_to_spotify = True

        wx.CallAfter(cb)

    def onSpotifyError(self, exception):
        if self._connected_to_spotify:
            self._connected_to_spotify = False
            if isinstance(exception, spotify.remote.exceptions.SpotifyRemoteError):
                utils.show_error(self, exception.error_description)
            else:
                utils.show_error(self, repr(exception))


def format_track_display(track):
    return '{0} - {1}'.format(seq(track.artists).first().name, track.name).replace('&', 'and')

