from ctypes import windll

import psutil


WM_COMMAND = 0x111
find_window = windll.User32.FindWindowW
send_message = windll.User32.SendMessageW

SPOTIFY_WINDOW_CLASS = 'SpotifyMainWindow'
WEB_HELPER_PROCESS = 'SpotifyWebHelper.exe'
SPOTIFY_PROCESS = 'Spotify.exe'

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
        raise SpotifyNotRunningError
    send_message(hwnd, WM_COMMAND, command_id, 0)


def get_web_helper_port():
    """
    Attempt to find the HTTPS port that the SpotifyWebHelper process is listening on.

    If SpotifyWebHelper.exe is not running, raises SpotifyNotRunningError.  Otherwise returns the port number.
    """
    # TODO: Find the listening port for Spotify.exe if the Web Helper isn't running
    helper_process = None
    for process in psutil.process_iter():
        if process.name() == WEB_HELPER_PROCESS:
            helper_process = process
            break

    if helper_process is None:
        raise SpotifyNotRunningError
    else:
        connections = sorted(helper_process.connections(), key=lambda conn: conn.laddr[1])
        return connections[0].laddr[1]


class SpotifyNotRunningError(Exception):
    """Raised when the HWND of the Spotify main window cannot be found."""
