import wx


class GUIAction:
    def __init__(self, label, callback, hotkey=None):
        self._widgets = []
        self.label = label
        self.callback = callback
        self.hotkey = hotkey

    def attach_widget(self, widget):
        self._widgets.append(widget)

    def set_label(self, label):
        for widget in self._widgets:
            self._set_label(widget, label)

    def _set_label(self, widget, label):
        if isinstance(widget, wx.MenuItem):
            if self.hotkey is not None:
                label = '{0}\t{1}'.format(label, self.hotkey)
            widget.SetItemLabel(label)
        else:
            widget.SetLabel(label)

