import ctypes


def save_hwnd(hwnd, path):
    with open(path, 'w') as f:
        f.write(str(hwnd))


def get_existing_hwnd(path):
    try:
        with open(path, 'r') as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return None
    except FileNotFoundError:
        return None


def focus_window(hwnd):
    ctypes.windll.User32.SetForegroundWindow(hwnd)

