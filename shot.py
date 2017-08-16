#!/usr/bin/env python3

import time
import PIL.ImageGrab
from ctypes import Structure, c_long, windll, pointer

u = windll.user32
WM_SETTEXT = 0x000C
WM_CLOSE = 0x0010
BM_CLICK = 0x00F5


class RECT(Structure):
    'RECT structure in Win32 API.'
    _fields_ = [(x, c_long) for x in ('left', 'top', 'right', 'bottom')]


def get_rect(hwnd):
    'Retrieves dimensions of the specified window.'
    r = RECT()
    assert u.GetWindowRect(hwnd, pointer(r))
    return (r.left, r.top, r.right, r.bottom)


def shot(hwnd):
    'Captures screenshot of the specified window.'
    return PIL.ImageGrab.grab(get_rect(hwnd))


def find_window(cls, parent=None):
    'Finds window or window control.'
    return u.FindWindowExW(parent, None, cls, None)


def query(train):
    'Queries information of the specified train number.'

    base = 'ThunderRT6'
    while True:
        hwnd = find_window(base + 'FormDC')
        if hwnd:
            break
        time.sleep(5)

    htext, hbutton = (
        find_window(base + x, hwnd)
        for x in ['TextBox', 'CommandButton']
    )

    u.SetForegroundWindow(hwnd)
    u.SendMessageW(htext, WM_SETTEXT, None, train)
    u.PostMessageW(hbutton, BM_CLICK, None, None)
    time.sleep(0.5)

    # close possible message box
    hmsg = find_window('#32770', None)
    if hmsg:
        u.SendMessageW(hmsg, WM_CLOSE, None, None)
        time.sleep(0.1)
        raise LookupError

    return shot(hwnd)


if __name__ == '__main__':
    for train in ('D1', 'G1'):
        query(train).show()
