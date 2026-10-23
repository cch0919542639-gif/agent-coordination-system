"""Windows owned-process primitive. No task lifecycle, shell, or worker selection."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
from functools import lru_cache
import math
import os
from pathlib import Path
import shutil
import subprocess
import time


class GuardError(RuntimeError):
    """Safe category only: never include argv, cwd or process output."""


class SecurityAttributes(C.Structure):
    _fields_ = [("length", W.DWORD), ("descriptor", W.LPVOID), ("inherit", W.BOOL)]


class StartupInfo(C.Structure):
    _fields_ = [("cb", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR),
                ("title", W.LPWSTR), ("x", W.DWORD), ("y", W.DWORD),
                ("width", W.DWORD), ("height", W.DWORD), ("chars_x", W.DWORD),
                ("chars_y", W.DWORD), ("fill", W.DWORD), ("flags", W.DWORD),
                ("show", W.WORD), ("reserved_size", W.WORD),
                ("reserved_bytes", C.POINTER(W.BYTE)),
                ("stdin", W.HANDLE), ("stdout", W.HANDLE), ("stderr", W.HANDLE)]


class StartupInfoEx(C.Structure):
    _fields_ = [("startup", StartupInfo), ("attributes", W.LPVOID)]


class ProcessInfo(C.Structure):
    _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE),
                ("pid", W.DWORD), ("tid", W.DWORD)]


class BasicLimits(C.Structure):
    _fields_ = [("process_time", C.c_int64), ("job_time", C.c_int64),
                ("flags", W.DWORD), ("minimum", C.c_size_t), ("maximum", C.c_size_t),
                ("active_limit", W.DWORD), ("affinity", C.c_size_t),
                ("priority", W.DWORD), ("scheduling", W.DWORD)]


class ExtendedLimits(C.Structure):
    _fields_ = [("basic", BasicLimits), ("io", C.c_uint64 * 6),
                ("process_memory", C.c_size_t), ("job_memory", C.c_size_t),
                ("peak_process_memory", C.c_size_t), ("peak_job_memory", C.c_size_t)]


class Accounting(C.Structure):
    _fields_ = [("user", C.c_int64), ("kernel", C.c_int64),
                ("period_user", C.c_int64), ("period_kernel", C.c_int64),
                ("faults", W.DWORD), ("total", W.DWORD),
                ("active", W.DWORD), ("terminated", W.DWORD)]


@lru_cache(maxsize=1)
def kernel32():
    if os.name != "nt":
        raise GuardError("platform_unsupported")
    api = C.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CloseHandle": ([W.HANDLE], W.BOOL),
        "CreateJobObjectW": ([W.LPVOID, W.LPCWSTR], W.HANDLE),
        "SetInformationJobObject": ([W.HANDLE, C.c_int, W.LPVOID, W.DWORD], W.BOOL),
        "QueryInformationJobObject": ([W.HANDLE, C.c_int, W.LPVOID, W.DWORD, W.LPVOID], W.BOOL),
        "TerminateJobObject": ([W.HANDLE, W.UINT], W.BOOL),
        "InitializeProcThreadAttributeList": ([W.LPVOID, W.DWORD, W.DWORD, C.POINTER(C.c_size_t)], W.BOOL),
        "UpdateProcThreadAttribute": ([W.LPVOID, W.DWORD, C.c_size_t, W.LPVOID, C.c_size_t, W.LPVOID, W.LPVOID], W.BOOL),
        "DeleteProcThreadAttributeList": ([W.LPVOID], None),
        "CreateFileW": ([W.LPCWSTR, W.DWORD, W.DWORD, C.POINTER(SecurityAttributes), W.DWORD, W.DWORD, W.HANDLE], W.HANDLE),
        "CreatePipe": ([C.POINTER(W.HANDLE), C.POINTER(W.HANDLE), C.POINTER(SecurityAttributes), W.DWORD], W.BOOL),
        "SetHandleInformation": ([W.HANDLE, W.DWORD, W.DWORD], W.BOOL),
        "CreateProcessW": ([W.LPCWSTR, W.LPWSTR, W.LPVOID, W.LPVOID, W.BOOL, W.DWORD,
                            W.LPVOID, W.LPCWSTR, C.POINTER(StartupInfoEx), C.POINTER(ProcessInfo)], W.BOOL),
        "ResumeThread": ([W.HANDLE], W.DWORD),
        "WaitForSingleObject": ([W.HANDLE, W.DWORD], W.DWORD),
        "GetExitCodeProcess": ([W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
        "GetProcessTimes": ([W.HANDLE, C.POINTER(W.FILETIME), C.POINTER(W.FILETIME),
                             C.POINTER(W.FILETIME), C.POINTER(W.FILETIME)], W.BOOL),
        "OpenProcess": ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
        "IsProcessInJob": ([W.HANDLE, W.HANDLE, C.POINTER(W.BOOL)], W.BOOL),
    }
    for name, (args, result) in signatures.items():
        method = getattr(api, name)
        method.argtypes, method.restype = args, result
    return api


def checked(result, category):
    if not result:
        raise GuardError(f"{category}:winerror_{C.get_last_error()}")
    return result


def creation_time(handle):
    values = [W.FILETIME() for _ in range(4)]
    checked(kernel32().GetProcessTimes(handle, *(C.byref(v) for v in values)), "process_times_failed")
    return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime


def identity_state(pid, expected_creation_time):
    """A reopened PID is observation only, never a termination authority."""
    if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF or type(expected_creation_time) is not int or expected_creation_time <= 0:
        return "unknown"
    api = kernel32()
    handle = api.OpenProcess(0x100000 | 0x1000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED
    if not handle:
        return "missing" if C.get_last_error() == 87 else "unknown"
    try:
        if creation_time(handle) != expected_creation_time:
            return "replaced"
        result = api.WaitForSingleObject(handle, 0)
        return {0: "exited", 258: "running"}.get(result, "unknown")
    except GuardError:
        return "unknown"
    finally:
        api.CloseHandle(handle)


class JobProcess:
    """Suspended launcher, assigned to a private Job *during* CreateProcessW.

    The current controller owns the only Job handle; it is not inheritable.
    No post-spawn Assign fallback: unsupported JOB_LIST fails before execution.
    """

    def __init__(self, command, *, cwd, capture_output=False):
        self.job = self.process = self.thread = None
        self.stdout = None
        self.members = {}
        self.returncode = None
        self.resumed = False
        self.api = kernel32()
        if (not isinstance(command, (list, tuple)) or not command
                or any(not isinstance(arg, str) or "\0" in arg for arg in command)):
            raise GuardError("invalid_argv")
        executable = shutil.which(command[0]) if command[0] else None
        if not executable or Path(executable).suffix.lower() != ".exe":
            raise GuardError("native_executable_required")
        argv = [str(Path(executable).resolve()), *command[1:]]
        command_line = subprocess.list2cmdline(argv)
        if len(command_line.encode("utf-16-le")) // 2 >= 32767:
            raise GuardError("argv_too_large")
        child_handles = []
        attributes = None
        attributes_ready = False
        read_handle = W.HANDLE()
        try:
            self.job = checked(self.api.CreateJobObjectW(None, None), "job_create_failed")
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE; no breakaway flags
            checked(self.api.SetInformationJobObject(self.job, 9, C.byref(limits), C.sizeof(limits)), "job_limits_failed")
            security = SecurityAttributes(C.sizeof(SecurityAttributes), None, True)
            for access in (0x80000000, 0x40000000):
                handle = self.api.CreateFileW("NUL", access, 3, C.byref(security), 3, 0x80, None)
                if handle in (None, C.c_void_p(-1).value):
                    raise GuardError("null_handle_failed")
                child_handles.append(handle)
            stdin_handle, null_output = child_handles
            stdout_handle = null_output
            if capture_output:
                write_handle = W.HANDLE()
                checked(self.api.CreatePipe(C.byref(read_handle), C.byref(write_handle), C.byref(security), 0), "pipe_create_failed")
                child_handles.append(write_handle.value)
                checked(self.api.SetHandleInformation(read_handle, 1, 0), "pipe_inheritance_failed")
                stdout_handle = write_handle.value
            startup = StartupInfoEx()
            startup.startup.cb = C.sizeof(StartupInfoEx)
            startup.startup.flags = 0x100  # STARTF_USESTDHANDLES
            startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = stdin_handle, stdout_handle, null_output
            size = C.c_size_t()
            self.api.InitializeProcThreadAttributeList(None, 2, 0, C.byref(size))
            if not size.value:
                raise GuardError("attributes_size_failed")
            attributes = C.create_string_buffer(size.value)
            checked(self.api.InitializeProcThreadAttributeList(attributes, 2, 0, C.byref(size)), "attributes_init_failed")
            attributes_ready = True
            startup.attributes = C.cast(attributes, W.LPVOID)
            jobs = (W.HANDLE * 1)(self.job)
            handles = (W.HANDLE * len(child_handles))(*child_handles)
            checked(self.api.UpdateProcThreadAttribute(attributes, 0, 0x2000D, jobs, C.sizeof(jobs), None, None), "job_attribute_failed")
            checked(self.api.UpdateProcThreadAttribute(attributes, 0, 0x20002, handles, C.sizeof(handles), None, None), "handles_attribute_failed")
            info = ProcessInfo()
            checked(self.api.CreateProcessW(argv[0], C.create_unicode_buffer(command_line), None, None, True,
                                           0x80000 | 0x4 | 0x8000000, None, str(Path(cwd).resolve()),
                                           C.byref(startup), C.byref(info)), "process_create_failed")
            self.process, self.thread, self.pid = info.process, info.thread, info.pid
            self.creation_time = creation_time(self.process)
            if capture_output:
                import msvcrt
                fd = msvcrt.open_osfhandle(read_handle.value, os.O_RDONLY | os.O_BINARY)
                read_handle = W.HANDLE()  # fd now owns the read handle
                self.stdout = os.fdopen(fd, "rb", buffering=0)
        except BaseException:
            self.close()
            raise
        finally:
            if attributes_ready:
                self.api.DeleteProcThreadAttributeList(attributes)
            for handle in child_handles:
                self.api.CloseHandle(handle)
            if read_handle.value:
                self.api.CloseHandle(read_handle)

    def resume(self):
        if self.resumed:
            raise GuardError("already_resumed")
        result = self.api.ResumeThread(self.thread)
        if result != 1:
            raise GuardError("resume_failed")
        self.resumed = True
        self.api.CloseHandle(self.thread)
        self.thread = None

    def wait(self, timeout=0):
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 <= timeout <= 7200:
            raise GuardError("invalid_wait_timeout")
        result = self.api.WaitForSingleObject(self.process, math.ceil(timeout * 1000))
        if result == 258:
            raise subprocess.TimeoutExpired("owned_worker", timeout)
        if result != 0:
            raise GuardError("process_wait_failed")
        code = W.DWORD()
        checked(self.api.GetExitCodeProcess(self.process, C.byref(code)), "process_exit_failed")
        self.returncode = code.value  # 259 is a valid exit code after a signaled wait
        return self.returncode

    def active_processes(self):
        value = Accounting()
        checked(self.api.QueryInformationJobObject(self.job, 1, C.byref(value), C.sizeof(value), None), "job_query_failed")
        return value.active

    def retain_members(self):
        # Retain real Job member handles before termination; never kill a reopened PID.
        self.members_exited()
        capacity = 32
        while capacity <= 4096:
            buffer = C.create_string_buffer(8 + capacity * C.sizeof(C.c_size_t))
            if self.api.QueryInformationJobObject(self.job, 3, buffer, C.sizeof(buffer), None):
                count = C.c_uint32.from_buffer(buffer, 4).value
                if count > capacity:
                    raise GuardError("job_members_invalid")
                pids = (C.c_size_t * count).from_buffer(buffer, 8)
                for pid in pids:
                    if pid == self.pid or pid in self.members:
                        continue
                    handle = self.api.OpenProcess(0x101000, False, pid)
                    if not handle:
                        if C.get_last_error() == 87:
                            continue
                        raise GuardError("job_member_open_failed")
                    inside = W.BOOL()
                    try:
                        checked(self.api.IsProcessInJob(handle, self.job, C.byref(inside)), "job_member_identity_failed")
                        if inside.value:
                            self.members[pid] = handle
                            handle = None
                    finally:
                        if handle:
                            self.api.CloseHandle(handle)
                return
            if C.get_last_error() != 234:  # ERROR_MORE_DATA: retry, never truncate
                raise GuardError("job_members_query_failed")
            capacity *= 2
        raise GuardError("job_member_budget_exceeded")

    def members_exited(self):
        for pid, handle in list(self.members.items()):
            result = self.api.WaitForSingleObject(handle, 0)
            if result == 0:
                self.api.CloseHandle(handle)
                del self.members[pid]
            elif result != 258:
                raise GuardError("job_member_wait_failed")
        return not self.members

    def wait_empty(self, timeout=0.25):
        # A signaled root handle may precede Job accounting rundown briefly.
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 <= timeout <= 10:
            raise GuardError("invalid_stop_timeout")
        deadline = time.monotonic() + timeout
        while True:
            self.retain_members()
            members_gone = self.members_exited()
            if self.active_processes() == 0 and members_gone:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))

    def stop(self, timeout=3):
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 10:
            raise GuardError("invalid_stop_timeout")
        inspection_error = None
        try:
            self.retain_members()
        except GuardError as exc:
            inspection_error = exc
        checked(self.api.TerminateJobObject(self.job, 1), "job_terminate_failed")
        if inspection_error is not None:
            raise inspection_error
        deadline = time.monotonic() + timeout
        while True:
            budget = deadline - time.monotonic()
            if budget <= 0:
                raise GuardError("tree_stop_unconfirmed")
            try:
                code = self.wait(min(0.02, budget))
            except subprocess.TimeoutExpired:
                continue
            self.retain_members()
            members_gone = self.members_exited()
            if self.active_processes() == 0 and members_gone:
                return code
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))

    def close(self):
        # Last Job close also covers constructor errors and a suspended launcher.
        for name in ("job", "thread", "process"):
            handle = getattr(self, name, None)
            if handle:
                self.api.CloseHandle(handle)
                setattr(self, name, None)
        for handle in self.members.values():
            self.api.CloseHandle(handle)
        self.members.clear()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
