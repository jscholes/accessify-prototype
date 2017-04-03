import wx
import wx.adv

from .utils import find_last_child


class KeyboardAccessibleNotebook(wx.Notebook):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_child_focussed = False
        self._control_down = False
        self.Bind(wx.EVT_NAVIGATION_KEY, self.onNavigationKey)
        self.Bind(wx.EVT_KEY_DOWN, self.onKey)
        self.Bind(wx.EVT_KEY_UP, self.onKey)

    def AddPage(self, page, *args, **kwargs):
        last_child = find_last_child(page)
        if last_child:
            last_child.Bind(wx.EVT_KILL_FOCUS, self.onLastChildFocusLost)
            last_child.Bind(wx.EVT_SET_FOCUS, self.onLastChildFocusGained)
            page.Bind(wx.EVT_NAVIGATION_KEY, self.onPageNavigationKey)
            page.Bind(wx.EVT_KEY_DOWN, self.onKey)
            page.Bind(wx.EVT_KEY_UP, self.onKey)
        super().AddPage(page, *args, **kwargs)

    def onNavigationKey(self, event):
        if not event.GetDirection() and self.FindFocus() == self and not self._control_down:
            last_child = find_last_child(self.GetCurrentPage())
            if last_child is not None:
                last_child.SetFocus()
                return
        event.Skip()

    def onKey(self, event):
        self._control_down = event.ControlDown()
        event.Skip()

    def onPageNavigationKey(self, event):
        if event.GetDirection() and self._last_child_focussed:
            self.SetFocus()
        else:
            event.Skip()

    def onLastChildFocusLost(self, event):
        self._last_child_focussed = False
        event.Skip()

    def onLastChildFocusGained(self, event):
        self._last_child_focussed = True
        event.Skip()


NOTE_COLLAPSED = 'collapsed'
NOTE_EXPANDED = 'expanded'
STATE_COLLAPSED = 0
STATE_EXPANDED = 1


class PopupChoiceButton(wx.adv.CommandLinkButton):
    """
    A PopupChoiceButton allows the user to select from a group of choices either via a context menu or by using the left and right arrow keys to cycle through the available choices while the control has focus.

    This control inherits from wx.adv.CommandLinkButton, but provides a similar API to other controls which also allow the user to select from a list of choices e.g. wx.ListBox or wx.Choice.

    The control currently does not offer item sorting, nor the ability to insert an item at a specific position.

    Methods accepting an itemIndex parameter will raise IndexError if itemIndex is less than, greater than or equal to the number of items in the control.  You can obtain the number of items with GetCount.
    """

    def __init__ (self, parent, id=wx.ID_ANY, mainLabel='', note='', pos=wx.DefaultPosition, size=wx.DefaultSize, choices=None, style=wx.WANTS_CHARS, validator=wx.DefaultValidator, name='popupchoicebutton'):
        super().__init__(parent=parent, id=id, mainLabel=mainLabel, note=note, pos=pos, size=size, style=style, validator=validator, name=name)
        self._label_prefix = self.GetLabel()
        if not choices:
            choices = []
        self._initialiseMenu()
        self._initialiseChoices(choices)
        self._bindEvents()
        self.SetState(STATE_COLLAPSED)

    def _initialiseMenu(self):
        self.menu = wx.Menu()

    def _initialiseChoices(self, choices):
        self._items = []
        self._item_ids = []
        self._selected_item_index = -1

        for choice in choices:
            self.Append(choice)

    def _bindEvents(self):
        self.Bind(wx.EVT_BUTTON, self.onClick)
        self.Bind(wx.EVT_KEY_DOWN, self.onChoiceSelectedFromKeyboard)
        self.menu.Bind(wx.EVT_MENU, self.onChoiceSelectedFromMenu)

    def Append(self, item, clientData=None):
        """
        Append a string item into the control with optional clientData.
        """
        item_dict = {'label': item}
        if clientData is not None:
            item_dict.update(data=clientData)
        self._items.append(item_dict)
        wx_id = wx.NewId()
        self._item_ids.append(wx_id)
        self.menu.AppendRadioItem(wx_id, item)

        if self._selected_item_index == -1:
            self.SetSelection(0)

    def GetClientData(self, itemIndex):
        """
        Retrieve the client data associated with the item at the given index (if any).
        """
        return self._items[itemIndex].get('data', None)

    def GetCount(self):
        """
        Retrieve the number of items in the control.
        """
        return len(self._items)

    def GetSelection(self):
        """
        Retrieve the index of the currently-selected item or wx.NOT_FOUND if no item is selected.
        """
        return self._selected_item_index

    def GetString(self, itemIndex):
        """
        Retrieve the label of the item with the given index.
        """
        return self._items[itemIndex]['label']

    def GetStrings(self):
        """
        Retrieve a list of the labels of all items in the control.
        """
        return [item['label'] for item in self._items]

    def GetStringSelection(self):
        """
        Retrieve the label of the currently-selected item or an empty string if no item is selected.
        """
        try:
            return self.GetString(self._selected_item_index)
        except IndexError:
            return ''

    def SetClientData(self, itemIndex, clientData):
        """
        Associate the given client data with the item at the given index.
        """
        self._items[itemIndex].update(data=clientData)

    def SetSelection(self, itemIndex):
        """
        Select the item at the given index.
        """
        if itemIndex >= self.GetCount() or itemIndex < 0:
            raise IndexError

        self._selected_item_index = itemIndex
        menu_item = self.menu.FindItemById(self._item_ids[itemIndex])
        if menu_item:
            menu_item.Check()
        self.SetLabel('{0}: {1}'.format(self._label_prefix, wx.MenuItem.GetLabelText(self._items[itemIndex]['label'])))

    def SetState(self, state):
        self._state = state
        if self._state == STATE_COLLAPSED:
            self.SetNote(NOTE_COLLAPSED)
        else:
            self.SetNote(NOTE_EXPANDED)

    def SetString(self, itemIndex, string):
        """
        Set the label for the item with the given index.
        """
        self._items[itemIndex].update(label=string)

    def onChoiceSelectedFromKeyboard(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_LEFT:
            self.SetSelection((self._selected_item_index - 1) % len(self._items))
        elif key == wx.WXK_RIGHT:
            self.SetSelection((self._selected_item_index + 1) % len(self._items))
        elif key == wx.WXK_RETURN:
            # TODO: Work out why this makes the default Windows beep sound
            self.onClick(None)
        else:
            if not self.HandleAsNavigationKey(event):
                event.Skip()

    def onChoiceSelectedFromMenu(self, event):
        selected = event.GetId()
        if selected is not None:
            self.SetSelection(self._item_ids.index(selected))

    def onClick(self, event):
        self.SetState(STATE_EXPANDED)
        self.PopupMenu(self.menu, (0, 0))
        self.SetState(STATE_COLLAPSED)

    def __len__(self):
        return self.GetCount()

