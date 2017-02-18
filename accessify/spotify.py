from ctypes import windll


WM_COMMAND = 0x111
find_window = windll.User32.FindWindowW
send_message = windll.User32.SendMessageW

SPOTIFY_WINDOW_CLASS = 'SpotifyMainWindow'
CMD_PLAY_PAUSE = 114
CMD_PREV_TRACK = 116
CMD_NEXT_TRACK = 115
CMD_SEEK_BACKWARD = 118
CMD_SEEK_FORWARD = 117
CMD_VOLUME_UP = 121
CMD_VOLUME_DOWN = 122


def play_pause():
    send_command(CMD_PLAY_PAUSE)


def previous_track():
    send_command(CMD_PREV_TRACK)


def next_track():
    send_command(CMD_NEXT_TRACK)


def seek_backwards():
    send_command(CMD_SEEK_BACKWARD)


def seek_forwards():
    send_command(CMD_SEEK_FORWARD)


def decrease_volume():
    send_command(CMD_VOLUME_DOWN)


def increase_volume():
    send_command(CMD_VOLUME_UP)


def send_command(command_id):
    hwnd = find_window(SPOTIFY_WINDOW_CLASS, None)
    if hwnd == 0:
        raise SpotifyWindowNotFoundError
    send_message(hwnd, WM_COMMAND, command_id, 0)


class WindowNotFoundError(Exception):
    """Raised when the HWND of the Spotify main window cannot be found."""
