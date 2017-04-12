import wx

from .. import constants
from .. import spotify


TITLE_SPOTIFY_ERROR = constants.APP_NAME
TXT_NOT_LOGGED_IN = 'Either the Spotify application isn\'t running or there\'s no user logged into it.  Please make sure the application is running and logged into a Spotify account.\nThis dialog will close once a connection has been made.'
TXT_UNEXPECTED_ERROR = 'Oops, something seems to have gone wrong with the Spotify application.  You may want to try restarting Spotify or logging out and then back in again.\nLeave this dialog open to keep trying to connect, or you can click Cancel to quit.\n\nError #{code} - {description}'
TXT_CONNECTION_ERROR = 'The Spotify application doesn\'t seem to be running.  Please start the application, make sure you\'re logged in and this dialog will close once a connection has been made.'


class SpotifyErrorDialog(wx.Dialog):
    def __init__(self, parent, exception, *args, **kwargs):
        super().__init__(parent=parent, title=TITLE_SPOTIFY_ERROR, *args, **kwargs)
        self._initialiseControls()
        self.SetException(exception)
        self.Centre()

    def _initialiseControls(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self)
        text_sizer = wx.BoxSizer(wx.VERTICAL)
        self.error_text = wx.StaticText(panel)
        text_sizer.Add(self.error_text, 1, wx.EXPAND | wx.ALL, 7)
        panel.SetSizerAndFit(text_sizer)
        button_sizer = wx.StdDialogButtonSizer()
        cancel_button = wx.Button(panel, wx.ID_CANCEL)
        cancel_button.Bind(wx.EVT_BUTTON, self.onCancel)
        button_sizer.AddButton(cancel_button)
        main_sizer.Add(panel, 1, wx.EXPAND | wx.ALL, 7)
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.BOTTOM | wx.RIGHT, 7)
        self.SetSizerAndFit(main_sizer)
        self.SetAutoLayout(True)
        self.SetEscapeId(wx.ID_CANCEL)

    def SetException(self, exception):
        self._exception = exception
        error_message = self.GetErrorMessage(exception)
        self.error_text.SetLabel(error_message)

    def GetErrorMessage(self, exception):
        if isinstance(exception, spotify.remote.exceptions.SpotifyRemoteError):
            if exception.error_code == '4110':
                error_message = TXT_NOT_LOGGED_IN
            else:
                error_message = TXT_UNEXPECTED_ERROR.format(code=exception.error_code, description=exception.error_description)
        else:
            error_message = TXT_CONNECTION_ERROR
        return error_message

    def onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

