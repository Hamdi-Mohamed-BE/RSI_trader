import asyncio
import importlib
import os
import re
from typing import Any, Protocol

PIPE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,180}$")


class DuplexPipeChannel(Protocol):
    def exchange(self, payload: bytes) -> bytes: ...

    def close(self) -> None: ...


class PyWin32PipeChannel:
    """A single persistent, newline-framed duplex Windows pipe connection."""

    def __init__(self, handle: Any, win32file: Any) -> None:
        self._handle = handle
        self._win32file = win32file
        self._buffer = bytearray()

    def write_line(self, payload: bytes) -> None:
        if not payload.endswith(b"\n"):
            raise ValueError("Named-pipe payloads must end with a newline.")
        self._win32file.WriteFile(self._handle, payload)
        self._win32file.FlushFileBuffers(self._handle)

    def read_line(self) -> bytes:
        while b"\n" not in self._buffer:
            _, chunk = self._win32file.ReadFile(self._handle, 65536)
            if not chunk:
                raise ConnectionError("The follower named pipe disconnected.")
            self._buffer.extend(chunk)
        line, remainder = self._buffer.split(b"\n", 1)
        self._buffer = bytearray(remainder)
        return bytes(line) + b"\n"

    def exchange(self, payload: bytes) -> bytes:
        self.write_line(payload)
        return self.read_line()

    def close(self) -> None:
        self._win32file.CloseHandle(self._handle)


class WindowsNamedPipeServer:
    """Creates local-only named-pipe servers compatible with MT5 FileOpen()."""

    @staticmethod
    def _modules() -> tuple[Any, Any, Any]:
        if os.name != "nt":
            raise RuntimeError("Windows named pipes are available only on Windows.")
        try:
            return (
                importlib.import_module("win32file"),
                importlib.import_module("win32pipe"),
                importlib.import_module("pywintypes"),
            )
        except ImportError as exc:
            raise RuntimeError("Install the project's Windows dependency group.") from exc

    @staticmethod
    def _validate_name(pipe_name: str) -> str:
        if not PIPE_NAME_PATTERN.fullmatch(pipe_name):
            raise ValueError(
                "Pipe names may contain only letters, numbers, dashes, and underscores."
            )
        return rf"\\.\pipe\{pipe_name}"

    async def accept(self, pipe_name: str) -> PyWin32PipeChannel:
        path = self._validate_name(pipe_name)
        win32file, win32pipe, pywintypes = self._modules()

        def create_and_connect() -> Any:
            handle = win32pipe.CreateNamedPipe(
                path,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
                1,
                65536,
                65536,
                0,
                None,
            )
            try:
                win32pipe.ConnectNamedPipe(handle, None)
            except pywintypes.error as exc:
                if exc.winerror != 535:  # ERROR_PIPE_CONNECTED
                    win32file.CloseHandle(handle)
                    raise
            return handle

        handle = await asyncio.to_thread(create_and_connect)
        return PyWin32PipeChannel(handle, win32file)
