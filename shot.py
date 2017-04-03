from ctypes import Structure, c_long, windll, pointer


class RECT(Structure):
    'RECT structure in Win32 API.'
    _fields_ = [(x, c_long) for x in ('left', 'top', 'right', 'bottom')]


def get_rect(*args):
    'Finds a window and retrieves its dimensions.'
    hwnd = windll.user32.FindWindowW(*args)
    r = RECT()
    windll.user32.GetWindowRect(hwnd, pointer(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)
