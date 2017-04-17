import functools
import threading

import wx


def find_last_child(widget):
    children = widget.GetChildren()
    if not children:
        return widget
    else:      
        last = children[len(children) - 1]
        return find_last_child(last)


def show_error(parent, message):
    if not wx.IsMainThread():
        raise RuntimeError('utils.show_error called from thread {0}, must only be called from main thread'.format(threading.current_thread().name))
    else:
        wx.MessageBox(message, 'Error', parent=parent, style=wx.ICON_ERROR)


def main_thread(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return wx.CallAfter(func, *args, **kwargs)
    return wrapper

