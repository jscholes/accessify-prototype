from collections import namedtuple

import wx

import spotify


WINDOW_TITLE = 'Accessify'

PlaybackButton = namedtuple('PlaybackButton', ['label', 'func'])


class MainWindow(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(parent=None, title=WINDOW_TITLE, *args, **kwargs)
        self.panel = wx.Panel(self)
        self.create_buttons()

    def create_buttons(self):
        self.buttons = {
            wx.NewId(): PlaybackButton('&Play/Pause', spotify.play_pause),
            wx.NewId(): PlaybackButton('P&revious', spotify.previous_track),
            wx.NewId(): PlaybackButton('&Next', spotify.next_track),
        }
        for id, button in self.buttons.items():
            btn = wx.Button(self.panel, id, button.label)
            btn.Bind(wx.EVT_BUTTON, self.onButtonPress)

    def onButtonPress(self, event):
        id = event.GetId()
        button = self.buttons[id]
        try:
            button.func()
        except spotify.WindowNotFoundError:
            show_error(self, 'Spotify doesn\'t seem to be running!')
        except spotify.CommandError as e:
            show_error(self, 'Error while sending command to Spotify.  Error code: {0}'.format(e.result))


def show_error(parent, message):
    wx.MessageBox(message, 'Error', parent=parent, style=wx.ICON_ERROR)


if __name__ == '__main__':
    app = wx.App()
    window = MainWindow()
    window.Show()
    app.MainLoop()
