import wx


def find_last_child(widget):
    children = widget.GetChildren()
    if not children:
        return widget
    else:      
        last = children[len(children) - 1]
        return find_last_child(last)


def show_error(parent, message):
    wx.CallAfter(wx.MessageBox, message, 'Error', parent=parent, style=wx.ICON_ERROR)

