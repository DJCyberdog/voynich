"""Windows DXGI process-local memory budget for a conservative DirectML profile.
Only a single unambiguous, non-software adapter with dedicated memory is eligible.
No claimed global free-VRAM measurement, no device reservation or OS mutation.
"""
import ctypes as c
import sys
import uuid
from contextlib import contextmanager

import vrs_hardware as h


class GUID(c.Structure):
    _fields_ = [('bytes', c.c_ubyte * 16)]

    @classmethod
    def from_string(cls, value):
        return cls((c.c_ubyte * 16).from_buffer_copy(uuid.UUID(value).bytes_le))


class LUID(c.Structure):
    _fields_ = [('low', c.c_uint32), ('high', c.c_int32)]


class Desc(c.Structure):
    _fields_ = [('description', c.c_wchar * 128), ('vendor', c.c_uint32),
                ('device', c.c_uint32), ('subsystem', c.c_uint32), ('revision', c.c_uint32),
                ('dedicated', c.c_size_t), ('dedicated_system', c.c_size_t),
                ('shared', c.c_size_t), ('luid', LUID), ('flags', c.c_uint32)]


class VideoMemory(c.Structure):
    _fields_ = [(key, c.c_uint64) for key in ('budget', 'usage', 'available_reservation', 'reservation')]


FACTORY1 = '770aae78-f26f-4dba-a829-253c83d1b387'
ADAPTER3 = '645967a4-1392-4310-a798-8053ce3e93fd'
NOT_FOUND = 0x887a0002


def _method(ptr, slot, result, *args):
    table = c.cast(ptr, c.POINTER(c.POINTER(c.c_void_p))).contents
    return c.WINFUNCTYPE(result, c.c_void_p, *args)(table[slot])


def _check(hr):
    if hr < 0:
        raise h.ResourceBlocked(f'DXGI HRESULT 0x{hr & 0xffffffff:08x}')


@contextmanager
def _owned(ptr):
    try:
        yield ptr
    finally:
        if ptr.value:
            _method(ptr, 2, c.c_uint32)(ptr)


def enumerate_budgets():
    """Read local process budgets in this process, not in a helper subprocess."""
    if sys.platform != 'win32' or c.sizeof(c.c_void_p) != 8:
        raise h.ResourceBlocked('DXGI requires native Windows x64')
    lib = c.WinDLL('dxgi.dll', winmode=0x800)  # LOAD_LIBRARY_SEARCH_SYSTEM32
    create = lib.CreateDXGIFactory1
    create.argtypes = [c.POINTER(GUID), c.POINTER(c.c_void_p)]
    create.restype = c.c_int32
    factory = c.c_void_p()
    _check(create(c.byref(GUID.from_string(FACTORY1)), c.byref(factory)))
    rows = []
    with _owned(factory):
        for i in range(64):
            adapter = c.c_void_p()
            hr = _method(factory, 12, c.c_int32, c.c_uint32, c.POINTER(c.c_void_p))(factory, i, c.byref(adapter))
            if hr & 0xffffffff == NOT_FOUND:
                return rows
            _check(hr)
            with _owned(adapter):
                desc = Desc()
                _check(_method(adapter, 10, c.c_int32, c.POINTER(Desc))(adapter, c.byref(desc)))
                if desc.flags & 2:  # DXGI_ADAPTER_FLAG_SOFTWARE
                    continue
                a3 = c.c_void_p()
                _check(_method(adapter, 0, c.c_int32, c.POINTER(GUID), c.POINTER(c.c_void_p))(adapter, c.byref(GUID.from_string(ADAPTER3)), c.byref(a3)))
                with _owned(a3):
                    vm = VideoMemory()
                    _check(_method(a3, 14, c.c_int32, c.c_uint32, c.c_int32, c.POINTER(VideoMemory))(a3, 0, 0, c.byref(vm)))
                    rows.append(dict(name=desc.description, luid=(desc.luid.high,desc.luid.low), dedicated=desc.dedicated, budget=vm.budget, usage=vm.usage))
    raise h.ResourceBlocked('DXGI adapter enumeration did not terminate')


def memory(api, index, expected_luid=None, enumerate_fn=None):
    """Fail closed on hybrid/multi-adapter systems; no name-only mapping of multiple GPUs."""
    try:
        if index != 0 or api.device_count() != 1:
            raise h.ResourceBlocked('DirectML requires exactly one visible device')
        rows = (enumerate_fn or enumerate_budgets)()
        if len(rows) != 1:
            raise h.ResourceBlocked('Ambiguous or absent physical DXGI adapter')
        row = rows[0]
        name = api.device_name(index)
        if not isinstance(name,str) or not name.strip() or name.strip().casefold() != row['name'].strip().casefold():
            raise h.ResourceBlocked('DirectML/DXGI adapter identity not established')
        luid = tuple(row['luid'])
        if expected_luid is not None and tuple(expected_luid) != luid:
            raise h.ResourceBlocked('DXGI adapter identity changed')
        dedicated,budget,usage = (row[k] for k in ('dedicated','budget','usage'))
        if any(type(x) is not int or x < 0 for x in (dedicated,budget,usage)) or dedicated <= 0 or budget <= 0:
            raise h.ResourceBlocked('Dedicated GPU memory budget unavailable')
        total = min(dedicated,budget)
        return dict(ok=True,index=index,total=total,free=max(0,total-usage),luid=list(luid),
                    dedicated=dedicated,budget=budget,usage=usage,source='DXGI process-local budget')
    except (OSError,AttributeError,KeyError,TypeError,ValueError,RuntimeError) as exc:
        if isinstance(exc,h.ResourceBlocked): raise
        raise h.ResourceBlocked('DXGI memory query failed') from exc
