import wx

from ..spotify.utils import is_spotify_uri

from . import utils


LABEL_NOW_PLAYING = 'Now playing'
LABEL_URI = 'Spoti&fy URI'
LABEL_PLAY_URI = '&Play'
LABEL_QUEUE_URI = 'Add to &queue'


class NowPlayingPage(wx.Panel):
    def __init__(self, parent, playback_controller, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.playback = playback_controller
        self.InitialiseControls()

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
        if is_spotify_uri(uri):
            self.playback.play_uri( uri)
        else:
            utils.show_error(self, 'Not a valid Spotify URI.')

    def onPlay(self, event):
        self.onURIEntered(None)
        self.uri_field.SetFocus()

    def onQueue(self, event):
        self.playback.queue_uri(self.uri_field.GetValue())
        self.uri_field.Clear()
        self.uri_field.SetFocus()

