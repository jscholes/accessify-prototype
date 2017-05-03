from enum import Enum

from functional import seq
import wx

from accessify import constants
from accessify import spotify
from accessify import structures

from accessify.spotify.eventmanager import PlaybackState

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
MSG_NO_AUTHORISATION = 'You can\'t use {0} without a Spotify account.  The application will now exit.'.format(constants.APP_NAME)
MSG_SPOTIFY_NOT_RUNNING = '{0} uses the Spotify client to play content, but it doesn\'t seem to be running.  Please start it up, log into your account and then restart {0}.'.format(constants.APP_NAME)
MSG_UNKNOWN_CONTENT = 'Unknown Content'
ERROR_UNPLAYABLE_CONTENT = 'The URI {uri} couldn\'t be played.  The content might not be available in your country or an advert might currently be playing.'

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
        self.SetState(GUIState.LOADING)
        self.playback = playback_controller
        self.library = library_controller
        self.InitialiseControls()
        self.Centre()

        self._authorisation_dialog = None
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

    def SetState(self, new_state):
        self.state = new_state
        if new_state == GUIState.LOADING:
            speech.speak(MSG_LOADING)
        elif new_state == GUIState.OPERATIONAL:
            if not self.IsShown():
                self.Show()

    def UpdateTrackDisplay(self, track=None, unknown_content=False):
        if unknown_content:
            self.SetTitle('{0} - {1}'.format(WINDOW_TITLE, MSG_UNKNOWN_CONTENT))
        elif track is None:
            self.SetTitle(WINDOW_TITLE)
        else:
            self.SetTitle('{0} - {1}'.format(WINDOW_TITLE, format_track_display(track)))

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
        is_unknown = track is None
        self.UpdateTrackDisplay(track, unknown_content=is_unknown)

    @main_thread
    def onPlaybackStateChange(self, state, track):
        mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
        if state in (PlaybackState.PAUSED, PlaybackState.STOPPED):
            mi.SetItemLabel('P&lay\tCtrl+Space')
            self.UpdateTrackDisplay(None)
        elif state == PlaybackState.PLAYING:
            mi.SetItemLabel('P&ause\tCtrl+Space')
            self.UpdateTrackDisplay(track)

    @main_thread
    def onUnplayableContent(self, uri):
        utils.show_error(self, ERROR_UNPLAYABLE_CONTENT.format(uri=uri))

    @main_thread
    def onSpotifyConnectionEstablished(self, *args, **kwargs):
        if self._spotify_error_dialog is not None:
            self._spotify_error_dialog.EndModal(wx.ID_CLOSE)
            self._spotify_error_dialog.Destroy()
            self._spotify_error_dialog = None
        if self.state in (GUIState.AUTHORISED, GUIState.CONNECTING):
            self.SetState(GUIState.OPERATIONAL)
        else:
            self.SetState(GUIState.CONNECTED)

    @main_thread
    def onSpotifyError(self, exception):
        if self.state in (GUIState.LOADING, GUIState.CONNECTED, GUIState.AUTHORISED, GUIState.OPERATIONAL):
            self.SetState(GUIState.CONNECTING)
            self._spotify_error_dialog = dialogs.SpotifyErrorDialog(self, exception)
            result = self._spotify_error_dialog.ShowModal()
            if result == wx.ID_CANCEL:
                wx.MessageBox(MSG_NO_CONNECTION, constants.APP_NAME, parent=self, style=wx.ICON_INFORMATION)
                self.Close()

    @main_thread
    def onSpotifyNotRunning(self, *args, **kwargs):
        wx.MessageBox(MSG_SPOTIFY_NOT_RUNNING, constants.APP_NAME, parent=self, style=wx.ICON_INFORMATION)
        self.Close()

    @main_thread
    def onAuthorisationRequired(self, revoked=False):
        if self.state in (GUIState.LOADING, GUIState.CONNECTED, GUIState.AUTHORISED, GUIState.OPERATIONAL):
            self.SetState(GUIState.AUTHORISING)
            self._authorisation_dialog = dialogs.AuthorisationDialog(self, authorisation_callback=self.library.begin_authorisation, first_run=not revoked)
            result = self._authorisation_dialog.ShowModal()
            if result == wx.ID_CANCEL:
                wx.MessageBox(MSG_NO_AUTHORISATION, constants.APP_NAME, parent=self, style=wx.ICON_INFORMATION)
                self.Close()

    @main_thread
    def onAuthorisationCompleted(self, profile):
        if self._authorisation_dialog is not None:
            self._authorisation_dialog .EndModal(wx.ID_CLOSE)
            self._authorisation_dialog.Destroy()
            self._authorisation_dialog = None
        if self.state == GUIState.CONNECTED:
            self.SetState(GUIState.OPERATIONAL)
        else:
            self.SetState(GUIState.AUTHORISED)


def format_track_display(track):
    return '{0} - {1}'.format(seq(track.artists).first().name, track.name).replace('&', 'and')


class GUIState(Enum):
    LOADING = 1
    AUTHORISING = 2
    AUTHORISED = 3
    CONNECTING = 4
    CONNECTED = 5
    OPERATIONAL = 6
    CLOSING = 7

