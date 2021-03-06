import functools

import wx

from accessify import structures

from accessify.library import SearchType
from accessify.spotify.utils import is_spotify_uri
from accessify.utils.formatting import format_seconds

from accessify.gui import speech
from accessify.gui import utils
from accessify.gui import widgets


LABEL_SEARCH = 'Search'
LABEL_SEARCH_QUERY = 'S&earch'
LABEL_SEARCH_TYPE = 'Search &type'
LABEL_SEARCH_BUTTON = '&Search'
LABEL_RESULTS = '&Results'
LABEL_NO_RESULTS = 'No results'

MSG_QUEUED = 'Added to queue'
MSG_COPIED = 'Copied'

SEARCH_TYPES = [
    (SearchType.TRACK, '&Track'),
    (SearchType.ARTIST, '&Artist'),
    (SearchType.ALBUM, 'A&lbum'),
    (SearchType.PLAYLIST, '&Playlist'),
]


class SearchPage(wx.Panel):
    def __init__(self, parent, playback_controller, library_controller, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.library = library_controller
        self.playback = playback_controller

        self.context_menu_commands = {
            wx.NewId(): {'label': '&Play', 'method': self.playback.play_item, 'shortcut': 'Return'},
            wx.NewId(): {'label': '&Add to queue', 'method': self.playback.queue_item, 'shortcut': 'Ctrl+Return', 'message': MSG_QUEUED},
            wx.NewId(): {'label': '&Copy Spotify URI', 'method': self.playback.copy_item_uri, 'shortcut': 'Ctrl+C', 'message': MSG_COPIED},
        }

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
        self.results = SearchResultsList(parent=self, item_renderer=render_item_text, context_menu_commands=self.context_menu_commands)

    def _bindEvents(self):
        self.query_field.Bind(wx.EVT_TEXT_ENTER, self.onQueryEntered)
        self.search_button.Bind(wx.EVT_BUTTON, self.onSearch)

    def onQueryEntered(self, event):
        def results_cb(result_collection):
            self.results.SetCollection(result_collection)
            self.results.SetFocus()

        query = self.query_field.GetValue()
        if not query:
            return
        if is_spotify_uri(query):
            self.query_field.SetSelection(-1, -1)
            self.playback.play_uri(query)
        else:
            self.results.Clear()
            search_type = self.search_type.GetClientData(self.search_type.GetSelection())
            callback = functools.partial(wx.CallAfter, results_cb)
            self.library.perform_new_search(query, search_type, callback)

    def onSearch(self, event):
        self.onQueryEntered(None)


class SearchResultsList:
    def __init__(self, parent, item_renderer, context_menu_commands):
        self._parent = parent
        self.item_renderer = item_renderer
        self.context_menu_commands = context_menu_commands
        self._widget = wx.ListBox(parent, style=wx.LB_SINGLE)
        self._has_items = False
        self._createContextMenu()
        self._bindEvents()

    def _createContextMenu(self):
        context_menu = wx.Menu()
        accelerators = []
        for id, command_dict in self.context_menu_commands.items():
            label = command_dict['label']
            shortcut = command_dict.get('shortcut', None)
            if shortcut:
                accelerator = wx.AcceleratorEntry(cmd=id)
                accelerator.FromString(shortcut)
                accelerators.append(accelerator)
                label = '{0}\t{1}'.format(label, command_dict['shortcut'])
            context_menu.Append(id, label)
        shortcuts = wx.AcceleratorTable(accelerators)
        self._widget.SetAcceleratorTable(shortcuts)
        self.context_menu = context_menu

    def _bindEvents(self):
        self._widget.Bind(wx.EVT_CONTEXT_MENU, self.onContextMenu)
        self._parent.Bind(wx.EVT_MENU, self.onContextMenuCommand)

    def onContextMenu(self, event):
        if self.GetSelectedItem() is None:
            return
        else:
            self._widget.PopupMenu(self.context_menu, event.GetPosition())

    def onContextMenuCommand(self, event):
        if not self._has_items:
            return
        command_dict = self.context_menu_commands.get(event.GetId(), None)
        if command_dict:
            callback = command_dict['method']
            callback(self.GetSelectedItem())
            msg = command_dict.get('message', None)
            if msg and event.GetEventObject() == self._widget:
                speech.speak(msg)

    def IndicateNoItems(self):
        self._has_items = False
        self._widget.Append(LABEL_NO_RESULTS)
        self.SelectFirstItem()

    def SetCollection(self, collection):
        if len(collection) > 0:
            self.AddItems(collection)
        else:
            self.IndicateNoItems()

    def AddItems(self, items):
        for item in items:
            self.AddItem(item)
        if self.GetSelectedItem() is None:
            self.SelectFirstItem()

    def AddItem(self, item):
        item_text = self.item_renderer(item)
        self._widget.Append(item_text, clientData=item)
        self._has_items = True

    def Clear(self):
        self._widget.Clear()

    def GetSelectedItem(self):
        if not self._has_items:
            return None
        selected_item = self._widget.GetSelection()
        if selected_item != wx.NOT_FOUND:
            return self._widget.GetClientData(selected_item)
        else:
            return None

    def GetWidget(self):
        return self._widget

    def SelectFirstItem(self):
        self._widget.SetSelection(0)

    def SetFocus(self):
        self._widget.SetFocus()


def render_item_text(item):
    if isinstance(item, structures.Track):
        text = '{0} by {1} ({2})'.format(item.name, ', '.join([artist.name for artist in item.artists]), format_seconds(item.length))
    elif isinstance(item, structures.Album):
        text = '{0} by {1}'.format(item.name, ', '.join([artist.name for artist in item.artists]))
    elif isinstance(item, structures.Artist):
        text = item.name
    elif isinstance(item, structures.Playlist):
        text = '{0} ({1} tracks)'.format(item.name, item.total_tracks)
    return text

