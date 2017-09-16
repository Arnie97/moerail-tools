from ctypes import windll, addressof, create_string_buffer, sizeof, byref
from ctypes import c_char, c_char_p, c_long, Structure, pointer

u = windll.user32
k = windll.kernel32

WM_SETTEXT = 0x000C
WM_CLOSE = 0x0010
BM_CLICK = 0x00F5
VBM_WINDOWTITLEADDR = 0x1091

PROCESS_VM_READ = 0x10
PROCESS_VM_WRITE = 0x20
PROCESS_VM_OPERATION = 0x8
PROCESS_QUERY_INFORMATION = 0x400
PROCESS_READ_WRITE_QUERY = (
    PROCESS_VM_READ | PROCESS_VM_WRITE |
    PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION)

MEM_PRIVATE = 0x20000
MEM_COMMIT = 0x1000


class RECT(Structure):
    _fields_ = [(x, c_long) for x in ('left', 'top', 'right', 'bottom')]


class MEMORY_BASIC_INFORMATION(Structure):
    _fields_ = [
        ('BaseAddress', c_long),
        ('AllocationBase', c_long),
        ('AllocationProtect', c_long),
        ('RegionSize', c_long),
        ('State', c_long),
        ('Protect', c_long),
        ('lType', c_long),
    ]
