import wx

from ..library import SearchType
from ..spotify.utils import is_spotify_uri
from .. import structures

from . import utils
from . import widgets


LABEL_SEARCH = 'Search'
LABEL_SEARCH_QUERY = 'S&earch'
LABEL_SEARCH_TYPE = 'Search &type'
LABEL_SEARCH_BUTTON = '&Search'
LABEL_RESULTS = '&Results'
LABEL_PLAY_SELECTED = '&Play\tReturn'

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


class SearchPage(wx.Panel):
    def __init__(self, parent, playback_controller, library_controller, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.library = library_controller
        self.playback = playback_controller
        self.InitialiseControls()

    def InitialiseControls(self):
        self._createSearchFields()
        self._createResultsList()
        self._bindEvents()

    def _createSearchFields(self):
        query_label = wx.StaticText(self, -1, LABEL_SEARCH_QUERY)
        self.query_field = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER|wx.TE_DONTWRAP)
        self.initial_focus = self.query_field

        self.search_type = widgets.PopupChoiceButton(self, mainLabel=LABEL_SEARCH_TYPE)
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
        if is_spotify_uri(query):
            self.query_field.SetSelection(-1, -1)
            self.playback.play_uri(query)
        else:
            self.results.Clear()
            search_type = self.search_type.GetClientData(self.search_type.GetSelection())
            self.library.perform_new_search(query, search_type, results_cb)

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
                utils.show_error(self, 'This result type is not yet supported')
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

