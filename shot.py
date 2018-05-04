#!/usr/bin/env python3

import time
import PIL.Image
import PIL.ImageGrab
from windows import *


def get_rect(hwnd):
    'Retrieves dimensions of the specified window.'
    r = RECT()
    assert u.GetWindowRect(hwnd, pointer(r))
    return (r.left, r.top, r.right, r.bottom)


def shot(hwnd):
    'Captures screenshot of the specified window.'
    return PIL.ImageGrab.grab(get_rect(hwnd))


def find_window(cls=None, parent=None):
    'Finds window or window control.'
    return u.FindWindowExW(parent, None, cls, None)


class Automation():
    'Emulate keyboard and mouse events and collect data from the executable.'

    def query(self, train):
        'Queries information of the specified train number.'
        u.SetForegroundWindow(self.hwnd)
        u.SendMessageW(self.htext, WM_SETTEXT, None, train)
        u.PostMessageW(self.hbutton, BM_CLICK, None, None)
        time.sleep(0.5)

        # close a possible message box
        hmsg = find_window('#32770')
        if hmsg:
            u.SendMessageW(hmsg, WM_CLOSE, None, None)
            time.sleep(0.1)
            raise LookupError

    def get_shot(self):
        'Crops the screenshot of the window.'
        img = shot(self.hwnd).convert('1', dither=False)
        img = img.crop((3, 22, 1030, 622))
        return PIL.Image.composite(img, self.empty, self.mask)

    def get_text(self, keyword='CR'):
        'Get label text from the window.'
        self._dump_heap()
        for obj in self._enum_vb_labels():
            try:
                caption = self._get_label_caption(obj)
                assert keyword in caption
            except AssertionError:
                pass
            else:
                return caption

    def __init__(self):
        'Get handles on the window and the process.'
        prefix = 'ThunderRT6'
        self.hwnd = find_window(prefix + 'FormDC')
        assert self.hwnd, 'Visual Basic window forms not found'
        self.htext = find_window(prefix + 'TextBox', self.hwnd)
        assert self.htext, 'Text boxes not found'
        self.hbutton = find_window(prefix + 'CommandButton', self.hwnd)
        assert self.hbutton, 'Command buttons not found'
        hmsg = find_window('#32770')
        assert not hmsg, 'Please close all the message boxes before running'

        pid = c_long()
        u.GetWindowThreadProcessId(self.hwnd, byref(pid))
        assert pid, 'Process not found'

        self.hproc = k.OpenProcess(PROCESS_READ_WRITE_QUERY, False, pid)
        assert self.hproc, 'Memory access denied'

        self.empty = PIL.Image.open('empty.png')
        self.mask = PIL.Image.open('mask.png')

    def __del__(self):
        if hasattr(self, 'hproc'):
            k.CloseHandle(self.hproc)

    def _dump_heap(self):
        'Dump the internal heap of the executable.'

        # Get the internal heap address of the form caption
        # This is done with a little undocumented SendMessage magic
        heap_addr = u.SendMessageW(self.hwnd, VBM_WINDOWTITLEADDR, None, None)

        # Get the heap at the form caption point
        mbi = MEMORY_BASIC_INFORMATION()
        mbi.BaseAddress = mbi.AllocationBase = heap_addr
        size = k.VirtualQueryEx(self.hproc, heap_addr, byref(mbi), sizeof(mbi))
        assert size == sizeof(mbi)

        # Now go back and get the address of the entire heap
        self.base_addr = base_addr = mbi.BaseAddress = mbi.AllocationBase
        mbi.RegionSize = 0
        size = k.VirtualQueryEx(self.hproc, base_addr, byref(mbi), sizeof(mbi))

        # A couple of sanity checks, just to be safe
        assert size == sizeof(mbi)
        assert mbi.lType == MEM_PRIVATE
        assert mbi.State == MEM_COMMIT
        assert mbi.RegionSize > 0

        # Dump the heap
        self.buffer = create_string_buffer(mbi.RegionSize)
        bytes_read = c_long()
        assert k.ReadProcessMemory(
            self.hproc, mbi.BaseAddress,
            self.buffer, mbi.RegionSize, byref(bytes_read))
        self.buf = bytearray(self.buffer)

    def _enum_vb_labels(self):
        'Parse the heap to get every label in the executable.'
        label = self._parse_label_class()
        base_addr_bytes = self._addr_to_bytes(0)
        i = 0
        while True:
            # Search for all references to label
            # (see internals.c for more details)
            i = self.buf.find(label, i)
            if i == -1:  # not found
                raise StopIteration
            else:
                obj_addr = i - 44

            # Check the base memory value to make sure it's really a VB object
            if self.buf[obj_addr:].startswith(base_addr_bytes):
                yield obj_addr

            i += 1  # Keep searching from the next byte

    def _parse_label_class(self):
        'Get the global address of the label class.'
        # Search for label->class_id (see internals.c for more details)
        assert b'VB.Label' in self.buf, 'Incompatible memory layout'
        cls_id_addr = self.buf.index(b'VB.Label')
        cls_id_addr_bytes = self._addr_to_bytes(cls_id_addr)

        # Search for &(label->class_id)
        cls_id_ptr_addr = self.buf.rindex(cls_id_addr_bytes, 0, cls_id_addr)

        # VBClass *label = (uint8_t *) &(label->class_id) - 36
        cls_struct_addr = cls_id_ptr_addr - 36
        return self._addr_to_bytes(cls_struct_addr)

    def _addr_to_bytes(self, n):
        'Convert relative address to absolute pointer (four bytes).'
        ctypes_long = c_long(self.base_addr + n)
        ctypes_array = (c_char * 4).from_address(addressof(ctypes_long))
        return bytearray(ctypes_array)

    def _get_label_caption(self, obj_addr):
        'Get caption of a label from its relative address.'
        caption_ptr_addr = addressof(self.buffer) + obj_addr + 136
        caption_addr = c_long.from_address(caption_ptr_addr).value
        assert caption_addr
        caption_addr += addressof(self.buffer) - self.base_addr
        caption = c_char_p(caption_addr).value
        return caption.decode('mbcs')


if __name__ == '__main__':
    me = Automation()
    for train in ('D1', 'G1'):
        me.query(train)
        me.get_shot().show()
        print(me.get_text())
