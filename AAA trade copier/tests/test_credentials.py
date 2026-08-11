import os
from pathlib import Path

import pytest

from trade_copier.services.credentials import MemoryCredentialVault, WindowsDpapiVault


def test_memory_vault_round_trip() -> None:
    vault = MemoryCredentialVault()
    reference = vault.store("not-written-to-disk")
    assert vault.retrieve(reference) == "not-written-to-disk"
    vault.delete(reference)
    assert reference not in vault.values


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI test")
def test_dpapi_vault_round_trip(tmp_path: Path) -> None:
    vault = WindowsDpapiVault(tmp_path / "vault")
    reference = vault.store("demo-terminal-password")
    assert reference.endswith(".cred")
    assert vault.retrieve(reference) == "demo-terminal-password"
    assert b"demo-terminal-password" not in (tmp_path / "vault" / reference).read_bytes()
    vault.delete(reference)
    assert not (tmp_path / "vault" / reference).exists()
