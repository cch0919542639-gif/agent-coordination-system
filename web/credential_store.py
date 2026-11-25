"""Windows user credential storage. Secrets never leave the server API."""
import ctypes
from ctypes import wintypes
import hashlib
import os


class CredentialError(Exception):
    pass


def target(root, user, provider, endpoint):
    value = '\0'.join((str(root), user, provider, endpoint)).encode('utf-8')
    return 'coordination-console/' + hashlib.sha256(value).hexdigest()


def _api():
    if os.name != 'nt': raise CredentialError('unavailable')
    class Credential(ctypes.Structure):
        _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                    ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                    ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                    ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
                    ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
                    ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR)]
    try:
        lib = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
    except OSError:
        raise CredentialError('unavailable') from None
    lib.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]; lib.CredWriteW.restype = wintypes.BOOL
    lib.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]; lib.CredReadW.restype = wintypes.BOOL
    lib.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]; lib.CredDeleteW.restype = wintypes.BOOL
    lib.CredFree.argtypes = [ctypes.c_void_p]; lib.CredFree.restype = None
    return lib, Credential


def save(name, secret):
    lib, Credential = _api()
    raw = secret.encode('ascii')
    data = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    row = Credential(Type=1, TargetName=name, CredentialBlobSize=len(raw), CredentialBlob=data, Persist=2)
    try:
        if not lib.CredWriteW(ctypes.byref(row), 0): raise CredentialError('write failed')
    finally:
        ctypes.memset(data, 0, len(raw))


def load(name):
    lib, Credential = _api()
    row = ctypes.POINTER(Credential)()
    if not lib.CredReadW(name, 1, 0, ctypes.byref(row)):
        if ctypes.get_last_error() == 1168: return None
        raise CredentialError('read failed')
    try:
        if not 1 <= row.contents.CredentialBlobSize <= 512: raise CredentialError('invalid credential')
        return ctypes.string_at(row.contents.CredentialBlob, row.contents.CredentialBlobSize).decode('ascii')
    except UnicodeError:
        raise CredentialError('invalid credential') from None
    finally:
        if row.contents.CredentialBlob and row.contents.CredentialBlobSize <= 2560:
            ctypes.memset(row.contents.CredentialBlob, 0, row.contents.CredentialBlobSize)
        lib.CredFree(row)


def delete(name):
    lib, _ = _api()
    if not lib.CredDeleteW(name, 1, 0) and ctypes.get_last_error() != 1168:
        raise CredentialError('delete failed')
