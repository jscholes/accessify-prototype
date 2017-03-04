import wx

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

