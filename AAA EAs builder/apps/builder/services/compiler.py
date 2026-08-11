import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.builder.models import CodeVersion


@dataclass(frozen=True)
class CompilationResult:
    status: str
    output: str
    compiled_at: datetime | None = None


def _source_includes_are_safe(source_code: str) -> bool:
    allowed_roots = {"Arrays", "Expert", "Indicators", "Math", "Trade"}
    includes = re.findall(r"^\s*#include\s*[<\"]([^>\"]+)[>\"]", source_code, re.MULTILINE)
    for include in includes:
        normalized = include.replace("/", "\\")
        root = normalized.split("\\", maxsplit=1)[0]
        if ".." in normalized or ":" in normalized or normalized.startswith("\\"):
            return False
        if root not in allowed_roots:
            return False
    return True


def compile_mql5_source(
    *, generation_id: str, filename: str, source_code: str
) -> CompilationResult:
    """Compile MQL5 without executing it, only when a local compiler is explicitly enabled."""
    if not settings.MQL5_COMPILER_ENABLED:
        return CompilationResult(
            CodeVersion.CompilationStatus.UNAVAILABLE,
            "MetaEditor compilation is disabled. Configure the isolated Windows compiler "
            "to enable it.",
        )

    metaeditor_path = Path(settings.METAEDITOR_PATH).expanduser().resolve()
    if not metaeditor_path.is_file():
        return CompilationResult(
            CodeVersion.CompilationStatus.UNAVAILABLE,
            "The configured MetaEditor executable was not found.",
        )
    if not _source_includes_are_safe(source_code) or "#import" in source_code:
        return CompilationResult(
            CodeVersion.CompilationStatus.FAILED,
            "Compilation refused because the source contains a non-allowlisted include or import.",
        )

    compile_root = Path(settings.MQL5_COMPILE_WORKDIR).expanduser().resolve()
    run_directory = (compile_root / generation_id).resolve()
    if compile_root not in run_directory.parents:
        return CompilationResult(
            CodeVersion.CompilationStatus.FAILED,
            "Compilation workspace validation failed.",
        )
    run_directory.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(filename).name
    source_path = run_directory / safe_filename
    log_path = run_directory / "compile.log"
    source_path.write_text(source_code, encoding="utf-8-sig")

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [
                str(metaeditor_path),
                f"/compile:{source_path}",
                f"/log:{log_path}",
            ],
            cwd=run_directory,
            capture_output=True,
            text=True,
            timeout=settings.MQL5_COMPILE_TIMEOUT_SECONDS,
            check=False,
            shell=False,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CompilationResult(
            CodeVersion.CompilationStatus.FAILED,
            f"MetaEditor could not complete: {type(exc).__name__}.",
            timezone.now(),
        )

    log_output = (
        log_path.read_text(encoding="utf-16", errors="replace") if log_path.exists() else ""
    )
    combined_output = "\n".join(
        part.strip() for part in (log_output, completed.stdout, completed.stderr) if part.strip()
    )[-20_000:]
    passed = completed.returncode == 0 and bool(
        re.search(r"\b0\s+errors?\b", combined_output, re.IGNORECASE)
    )
    return CompilationResult(
        CodeVersion.CompilationStatus.PASSED if passed else CodeVersion.CompilationStatus.FAILED,
        combined_output or "MetaEditor returned no compiler output.",
        timezone.now(),
    )
