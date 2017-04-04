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
LABEL_NO_RESULTS = 'No results'

SEARCH_TYPES = [
    (SearchType.TRACK, '&Track'),
    (SearchType.ARTIST, '&Artist'),
    (SearchType.ALBUM, 'A&lbum'),
    (SearchType.PLAYLIST, '&Playlist'),
]

context_menu_commands = {
    wx.NewId(): {'label': '&Play', 'method': 'PlaySelectedURI', 'shortcut': 'Return'},
    wx.NewId(): {'label': '&Add to queue', 'method': 'QueueSelectedURI'},
    wx.NewId(): {'label': '&Copy Spotify URI', 'method': 'CopySelectedURI', 'shortcut': 'Ctrl+C'},
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
        self.results = SearchResultsList(self)

    def _bindEvents(self):
        self.query_field.Bind(wx.EVT_TEXT_ENTER, self.onQueryEntered)
        self.search_button.Bind(wx.EVT_BUTTON, self.onSearch)

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

    def HandleResults(self, result_list):
        if result_list:
            self.AddResults(result_list)
        else:
            self.results.IndicateNoResults()
        self.results.SetFocus()

    def AddResults(self, results):
        for result in results:
            self.results.AddItem(result)
        if self.results.GetSelectedURI() is None:
            self.results.SelectFirstItem()

    def PlaySelectedURI(self):
        result_uri = self.results.GetSelectedURI()
        if result_uri:
            self.playback.play_uri(result_uri)

    def CopySelectedURI(self):
        result_uri = self.results.GetSelectedURI()
        if result_uri:
            self.playback.copy_uri(result_uri)

    def QueueSelectedURI(self):
        result_uri = self.results.GetSelectedURI()
        if result_uri:
            self.playback.queue_uri(result_uri)


class SearchResultsList:
    def __init__(self, parent):
        self._parent = parent
        self._widget = wx.ListBox(parent, style=wx.LB_SINGLE)
        self._has_items = False
        self._createContextMenu()
        self._bindEvents()

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
        self._widget.SetAcceleratorTable(shortcuts)
        self.context_menu = context_menu

    def _bindEvents(self):
        self._widget.Bind(wx.EVT_CONTEXT_MENU, self.onContextMenu)
        self._parent.Bind(wx.EVT_MENU, self.onContextMenuCommand)

    def GetWidget(self):
        return self._widget

    def onContextMenu(self, event):
        if self.GetSelectedURI() is None:
            return
        else:
            self._widget.PopupMenu(self.context_menu, event.GetPosition())

    def onContextMenuCommand(self, event):
        if not self._has_items:
            return
        command_dict = context_menu_commands.get(event.GetId(), None)
        if command_dict:
            getattr(self._parent, command_dict['method'])()

    def Clear(self):
        self._widget.Clear()

    def IndicateNoResults(self):
        self._has_items = False
        self._widget.Append(LABEL_NO_RESULTS)
        self.SelectFirstItem()

    def SetFocus(self):
        self._widget.SetFocus()

    def AddItem(self, item):
        if type(item) in (structures.Track, structures.Album):
            text = '{0} by {1}'.format(item.name, ', '.join([artist.name for artist in item.artists]))
        elif isinstance(item, structures.Artist):
            text = item.name
        elif isinstance(item, structures.Playlist):
            text = '{0} ({1} tracks)'.format(item.name, item.total_tracks)
        else:
            utils.show_error(self, 'This item type is not yet supported')
            return
        self._widget.Append(text, clientData=item.uri)
        self._has_items = True

    def SelectFirstItem(self):
        self._widget.SetSelection(0)

    def GetSelectedURI(self):
        if not self._has_items:
            return None
        selected_result = self._widget.GetSelection()
        if selected_result != wx.NOT_FOUND:
            result_uri = self._widget.GetClientData(selected_result)
            return result_uri
        else:
            return None

