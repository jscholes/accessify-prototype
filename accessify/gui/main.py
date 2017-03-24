from functional import seq
import wx

from ..search import SearchType
from .. import spotify
from .. import structures

from . import controls


WINDOW_TITLE = 'Accessify'
MENU_PLAYBACK = '&Playback'

LABEL_SEARCH = 'Search'
LABEL_SEARCH_QUERY = 'S&earch'
LABEL_SEARCH_TYPE = 'Search &type'
LABEL_SEARCH_BUTTON = '&Search'
LABEL_RESULTS = '&Results'
LABEL_PLAY_SELECTED = '&Play\tReturn'

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

SEARCH_TYPES = [
    (SearchType.TRACK, '&Track'),
    (SearchType.ARTIST, '&Artist'),
    (SearchType.ALBUM, 'A&lbum'),
    (SearchType.PLAYLIST, '&Playlist'),
]

ID_PLAY_SELECTED = wx.NewId()
ID_COPY_SELECTED = wx.NewId()
ID_QUEUE_SELECTED = wx.NewId()
context_menu_commands = {
    ID_PLAY_SELECTED: {'label': '&Play', 'method': 'PlaySelectedURI', 'shortcut': 'Return'},
    ID_QUEUE_SELECTED: {'label': 'Play ne&xt', 'method': 'QueueSelectedURI'},
    ID_COPY_SELECTED: {'label': '&Copy Spotify URI', 'method': 'CopySelectedURI', 'shortcut': 'Ctrl+C'},
}


class MainWindow(wx.Frame):
    def __init__(self, playback_controller, search_controller, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, *args, **kwargs)
        self.playback = playback_controller
        self.search = search_controller
        self.InitialiseControls()

    def InitialiseControls(self):
        self.panel = wx.Panel(self)
        self.tabs = self._createTabs()
        self._addPages()
        self._createMenus()
        self._bindEvents()

    def _createTabs(self):
        return controls.KeyboardAccessibleNotebook(self.panel, style=wx.NB_BOTTOM|wx.NB_NOPAGETHEME|wx.NB_FLAT)

    def         _addPages(self):
        self.tabs.AddPage(SearchPage(self.tabs, self.playback, self.search), LABEL_SEARCH)
        self.tabs.AddPage(NowPlayingPage(self.tabs, self.playback), LABEL_NOW_PLAYING)

    def _createMenus(self):
        playback_menu = playback_menu = wx.Menu()
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
        event_manager.subscribe(spotify.eventmanager.EventType.STOP, self.onStop)
        event_manager.subscribe(spotify.eventmanager.EventType.ERROR, self.onError)

    def UpdateTrackDisplay(self, track):
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

        wx.CallAfter(cb)

    def onPlay(self):
        # TODO: Remove this ugly hack with CallAfter decorator
        def cb():
            mi = self.playback_menu.FindItemById(ID_PLAY_PAUSE)
            mi.SetItemLabel('P&ause\tCtrl+Space')

        wx.CallAfter(cb)

    def onStop(self):
        wx.CallAfter(self.onPause)
        wx.CallAfter(self.UpdateTrackDisplay, None)

    def onError(self, exception):
        show_error(self, exception.error_description)


class TabsPage(wx.Panel):
    def __init__(self, parent, playback_controller, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.playback = playback_controller
        self.InitialiseControls()


class SearchPage(TabsPage):
    def __init__(self, parent, playback_controller, search_controller, *args, **kwargs):
        self.search = search_controller
        super().__init__(parent, playback_controller, *args, **kwargs)

    def InitialiseControls(self):
        self._createSearchFields()
        self._createResultsList()
        self._bindEvents()

    def _createSearchFields(self):
        query_label = wx.StaticText(self, -1, LABEL_SEARCH_QUERY)
        self.query_field = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER|wx.TE_DONTWRAP)
        self.initial_focus = self.query_field

        self.search_type = controls.PopupChoiceButton(self, mainLabel=LABEL_SEARCH_TYPE)
        for type, label in SEARCH_TYPES:
            self.search_type.Append(label, clientData=type)
        self.search_button = wx.Button(self, wx.ID_ANY, LABEL_SEARCH_BUTTON)

    def _createResultsList(self):
        results_label = wx.StaticText(self, -1, LABEL_RESULTS)
        self.results = wx.ListBox(self, style=wx.LB_SINGLE)
        self._createContextMenu()

    def _createContextMenu(self):
        context_menu = wx.Menu()
        accelerators = []
        for id, command_dict in context_menu_commands.items():
            context_menu.Append(id, command_dict['label'])
            shortcut = command_dict.get('shortcut', None)
            if shortcut:
                accelerator = wx.AcceleratorEntry(cmd=id)
                accelerator.FromString(shortcut)
                accelerators.append(accelerator)
        shortcuts = wx.AcceleratorTable(accelerators)
        self.results.SetAcceleratorTable(shortcuts)
        self.context_menu = context_menu

    def _bindEvents(self):
        self.query_field.Bind(wx.EVT_TEXT_ENTER, self.onQueryEntered)
        self.search_button.Bind(wx.EVT_BUTTON, self.onSearch)
        self.results.Bind(wx.EVT_CONTEXT_MENU, self.onContextMenu)
        self.Bind(wx.EVT_MENU, self.onContextMenuCommand)

    def onQueryEntered(self, event):
        def results_cb(result_list):
            wx.CallAfter(self.HandleResults, result_list)

        query = self.query_field.GetValue()
        if not query:
            return
        else:
            self.results.Clear()
            search_type = self.search_type.GetClientData(self.search_type.GetSelection())
            self.search.perform_new_search(query, search_type, results_cb)

    def onSearch(self, event):
        self.onQueryEntered(None)

    def onContextMenu(self, event):
        self.PopupMenu(self.context_menu, event.GetPosition())

    def onContextMenuCommand(self, event):
        command_dict = context_menu_commands.get(event.GetId(), None)
        if command_dict:
            getattr(self, command_dict['method'])()

    def HandleResults(self, result_list):
        if result_list:
            self.AddResults(result_list)
        else:
            self.results.Append('No results')
            self.results.SetSelection(0)
        self.results.SetFocus()

    def AddResults(self, results):
        for result in results:
            if type(result) in (structures.Track, structures.Album):
                text = '{0} by {1}'.format(result.name, ', '.join([artist.name for artist in result.artists]))
            elif isinstance(result, structures.Artist):
                text = result.name
            elif isinstance(result, structures.Playlist):
                text = '{0} ({1} tracks)'.format(result.name, result.total_tracks)
            else:
                show_error(self, 'This result type is not yet supported')
                return
            self.results.Append(text, clientData=result.uri)
        if self.GetSelectedURI() is None:
            self.results.SetSelection(0)

    def PlaySelectedURI(self):
        result_uri = self.GetSelectedURI()
        if result_uri:
            self.playback.play_uri(result_uri)

    def CopySelectedURI(self):
        result_uri = self.GetSelectedURI()
        if result_uri:
            self.playback.copy_uri(result_uri)

    def QueueSelectedURI(self):
        result_uri = self.GetSelectedURI()
        if result_uri:
            self.playback.queue_uri(result_uri)

    def GetSelectedURI(self):
        selected_result = self.results.GetSelection()
        if selected_result != wx.NOT_FOUND:
            result_uri = self.results.GetClientData(selected_result)
            return result_uri
        else:
            return None


class NowPlayingPage(TabsPage):
    def InitialiseControls(self):
        uri_label = wx.StaticText(self, -1, LABEL_URI)
        self.uri_field = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER|wx.TE_DONTWRAP)
        self.uri_field.Bind(wx.EVT_TEXT_ENTER, self.onURIEntered)
        self.initial_focus = self.uri_field

        self._addButtons()

    def _addButtons(self):
        play_button = wx.Button(self, wx.ID_ANY, LABEL_PLAY_URI)
        play_button.Bind(wx.EVT_BUTTON, self.onPlay)
        queue_button = wx.Button(self, wx.ID_ANY, LABEL_QUEUE_URI)
        queue_button.Bind(wx.EVT_BUTTON, self.onQueue)

    def onURIEntered(self, event):
        uri = self.uri_field.GetValue()
        self.uri_field.Clear()
        if uri:
            if uri.startswith('spotify:'):
                self.playback.play_uri( uri)
            else:
                show_error(self, 'Not a valid Spotify URI.')

    def onPlay(self, event):
        self.onURIEntered(None)
        self.uri_field.SetFocus()

    def onQueue(self, event):
        self.playback.queue_uri(self.uri_field.GetValue())
        self.uri_field.Clear()
        self.uri_field.SetFocus()


def show_error(parent, message):
    wx.CallAfter(wx.MessageBox, message, 'Error', parent=parent, style=wx.ICON_ERROR)


def format_track_display(track):
    return '{0} - {1}'.format(seq(track.artists).first().name, track.name).replace('&', 'and')

