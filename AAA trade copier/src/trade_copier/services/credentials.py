import base64
import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class CredentialVault(Protocol):
    def store(self, secret: str) -> str: ...

    def retrieve(self, reference: str) -> str: ...

    def delete(self, reference: str) -> None: ...


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


class WindowsDpapiVault:
    cryptprotect_ui_forbidden = 0x01

    def __init__(self, vault_dir: Path) -> None:
        if os.name != "nt":
            raise RuntimeError("Windows DPAPI is available only on Windows.")
        self.vault_dir = vault_dir.resolve()
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _blob(data: bytes) -> tuple[DataBlob, ctypes.Array[ctypes.c_char]]:
        buffer = ctypes.create_string_buffer(data)
        blob = DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
        return blob, buffer

    def _protect(self, plaintext: bytes) -> bytes:
        source, source_buffer = self._blob(plaintext)
        output = DataBlob()
        success = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(source),
            "AAA MT5 credential",
            None,
            None,
            None,
            self.cryptprotect_ui_forbidden,
            ctypes.byref(output),
        )
        if not success:
            raise ctypes.WinError()
        _ = source_buffer
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(output.pbData)

    def _unprotect(self, ciphertext: bytes) -> bytes:
        source, source_buffer = self._blob(ciphertext)
        output = DataBlob()
        success = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            self.cryptprotect_ui_forbidden,
            ctypes.byref(output),
        )
        if not success:
            raise ctypes.WinError()
        _ = source_buffer
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(output.pbData)

    def _path(self, reference: str) -> Path:
        if Path(reference).name != reference or not reference.endswith(".cred"):
            raise ValueError("Invalid credential reference.")
        path = (self.vault_dir / reference).resolve()
        if path.parent != self.vault_dir:
            raise ValueError("Credential reference escaped the vault directory.")
        return path

    def store(self, secret: str) -> str:
        if not secret:
            raise ValueError("Credential cannot be empty.")
        reference = f"{uuid4()}.cred"
        ciphertext = self._protect(secret.encode("utf-8"))
        self._path(reference).write_bytes(base64.b64encode(ciphertext))
        return reference

    def retrieve(self, reference: str) -> str:
        ciphertext = base64.b64decode(self._path(reference).read_bytes(), validate=True)
        return self._unprotect(ciphertext).decode("utf-8")

    def delete(self, reference: str) -> None:
        self._path(reference).unlink(missing_ok=True)


class MemoryCredentialVault:
    """Test-only vault that never writes credentials to disk."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def store(self, secret: str) -> str:
        reference = f"{uuid4()}.cred"
        self.values[reference] = secret
        return reference

    def retrieve(self, reference: str) -> str:
        return self.values[reference]

    def delete(self, reference: str) -> None:
        self.values.pop(reference, None)
