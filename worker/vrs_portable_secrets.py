"""Windows user-scoped DPAPI store; encrypted blobs only, never automatic injection."""
import ctypes
import getpass
import os
import re
from vrs_portable import local, need

SLOT=re.compile(r'VRS_(?:GITHUB_TOKEN|REVIEW_KEY)_[A-Z0-9_]{1,64}')


def dpapi(data, decrypt=False):
    need(os.name=='nt','DPAPI requires native Windows')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    buf=(ctypes.c_ubyte*len(data)).from_buffer_copy(data); src=Blob(len(data),buf); out=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True); kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p]; kernel.LocalFree.restype=ctypes.c_void_p
    fn=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]; fn.restype=wintypes.BOOL
    try:
        need(fn(ctypes.byref(src),None,None,None,None,1,ctypes.byref(out)), 'DPAPI operation failed')
        return ctypes.string_at(out.pbData,out.cbData)
    finally:
        ctypes.memset(buf,0,len(data))
        if out.pbData: ctypes.memset(out.pbData,0,out.cbData); kernel.LocalFree(out.pbData)


def path(root,slot):
    need(isinstance(slot,str) and SLOT.fullmatch(slot),'Invalid credential slot'); return local(root,'config/secrets/'+slot+'.dpapi')


def store(root,slot,value):
    import tempfile
    need(isinstance(value,str) and 0<len(value)<=4096 and not any(c.isspace() for c in value),'Invalid credential')
    p=path(root,slot); b=dpapi(value.encode('utf-8')); p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(b); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def read(root,slot):
    p=path(root,slot); need(p.is_file() and 0<p.stat().st_size<=65536,'Credential missing or invalid'); return dpapi(p.read_bytes(),True).decode('utf-8')


def prompt(root,slot):
    v=getpass.getpass('Credential (hidden): '); store(root,slot,v)
