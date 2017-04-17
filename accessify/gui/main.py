from functional import seq
import wx

from accessify import constants
from accessify import spotify
from accessify import structures

from accessify.gui import dialogs
from accessify.gui import nowplaying
from accessify.gui import search
from accessify.gui import speech
from accessify.gui import utils
from accessify.gui import widgets

from accessify.gui.utils import main_thread


WINDOW_TITLE = constants.APP_NAME
MENU_PLAYBACK = '&Playback'
MSG_LOADING = 'Loading...'
MSG_NO_CONNECTION = '{0} cannot function without the Spotify client.  The application will now exit.'.format(constants.APP_NAME)
ERROR_UNPLAYABLE_CONTENT = 'That content couldn\'t be played.  It might not be available in your country or an advert might be playing.'

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
        self.playback.set_error_callback(self.onSpotifyError)
        self.InitialiseControls()
        self.Centre()

        self._connected_to_spotify = False
        self._spotify_error_dialog = None

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
        # Don't bother with this for now
        #self.tabs.AddPage(nowplaying.NowPlayingPage(self.tabs, self.playback), nowplaying.LABEL_NOW_PLAYING)

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
        event_manager.subscribe(spotify.eventmanager.EventType.STOP, self.onPause)
        event_manager.subscribe(spotify.eventmanager.EventType.ERROR, self.onSpotifyError)

    def UpdateTrackDisplay(self, track):
        if track is None:
            self.SetTitle(WINDOW_TITLE)
        else:
            self.SetTitle('{0} - {1}'.format(WINDOW_TITLE, format_track_display(track)))
        if not self._connected_to_spotify:
            self._connected_to_spotify = True
            self._hideErrorDialog()
            self.Show()

    def _hideErrorDialog(self):
        if self._spotify_error_dialog is not None:
            self._spotify_error_dialog.EndModal(wx.ID_CLOSE)
            self._spotify_error_dialog.Destroy()
            self._spotify_error_dialog = None

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

    @main_thread
    def onTrackChange(self, track):
        self.UpdateTrackDisplay(track)

    @main_thread
    def onPause(self):
        mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
        mi.SetItemLabel('P&lay\tCtrl+Space')
        self.UpdateTrackDisplay(None)
        self._hideErrorDialog()
        self._connected_to_spotify = True

    @main_thread
    def onPlay(self, track):
        mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
        mi.SetItemLabel('P&ause\tCtrl+Space')
        self.UpdateTrackDisplay(track)
        self._hideErrorDialog()
        self._connected_to_spotify = True

    @main_thread
    def onSpotifyError(self, exception):
        if isinstance(exception, spotify.exceptions.ContentPlaybackError):
            utils.show_error(self, ERROR_UNPLAYABLE_CONTENT)
        else:
            if self._spotify_error_dialog is None:
                self._connected_to_spotify = False
                self._spotify_error_dialog = dialogs.SpotifyErrorDialog(self, exception)
                result = self._spotify_error_dialog.ShowModal()
                if result == wx.ID_CANCEL:
                    wx.MessageBox(MSG_NO_CONNECTION, constants.APP_NAME, parent=self, style=wx.ICON_INFORMATION)
                    self.Close()


def format_track_display(track):
    return '{0} - {1}'.format(seq(track.artists).first().name, track.name).replace('&', 'and')

