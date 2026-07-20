from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence


BACKEND_DIR = Path(__file__).resolve().parents[1]


def module_command(module: str, arguments: Sequence[str] = ()) -> list[str]:
    if not module or any(character.isspace() for character in module):
        raise ValueError("module must be a non-empty dotted Python path")
    return [sys.executable, "-m", module, *[str(value) for value in arguments]]


def run_module(
    module: str,
    arguments: Sequence[str] = (),
    *,
    timeout_seconds: int,
    environment: dict[str, str] | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    command = module_command(module, arguments)
    started = time.monotonic()
    completed = runner(
        command,
        cwd=BACKEND_DIR,
        env={**os.environ, **(environment or {})},
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    duration_seconds = round(time.monotonic() - started, 3)
    result = {
        "module": module,
        "arguments": list(arguments),
        "returncode": int(completed.returncode),
        "duration_seconds": duration_seconds,
        "stdout": str(completed.stdout or "").strip(),
        "stderr": str(completed.stderr or "").strip(),
    }
    if completed.returncode != 0:
        detail = result["stderr"] or result["stdout"] or "no output"
        raise RuntimeError(f"job_failed:{module}:exit_{completed.returncode}:{detail[-1000:]}")
    return result
