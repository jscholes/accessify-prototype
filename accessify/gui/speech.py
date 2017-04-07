import wx

import tolk


def speak(text):
    wx.CallAfter(tolk.speak, text, False)

