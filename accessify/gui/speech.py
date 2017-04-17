import tolk
import wx


def speak(text, delay_ms=0):
    if delay_ms <= 0:
        wx.CallAfter(tolk.speak, text, False)
    else:
        wx.CallLater(delay_ms, tolk.speak, text, False)

