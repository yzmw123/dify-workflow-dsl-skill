#!/usr/bin/env python3
"""Run validation with an isolated, reusable runtime (standard library only)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parents[1]
CHECK = "import sys; assert sys.version_info >= (3, 10); import yaml; assert 6 <= int(yaml.__version__.split('.')[0]) < 7"


def usable(python: Path) -> bool:
    try:
        return subprocess.run([str(python), "-c", CHECK], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, check=False).returncode == 0
    except OSError:
        return False


def main() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required. Select it when invoking run_validator.py.", file=sys.stderr)
        return 2
    args = sys.argv[1:]
    setup_only = args == ["--setup"]
    requirements = ROOT / "requirements.txt"
    try:
        fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()[:12]
        cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        target = Path(os.environ.get("DIFY_DSL_VENV_DIR", cache / "dify-workflow-dsl" /
                      f"py{sys.version_info.major}.{sys.version_info.minor}-{fingerprint}"))
        python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not usable(python):
            if os.environ.get("DIFY_DSL_OFFLINE") == "1":
                print(f"Runtime is not ready at {target}. Run without DIFY_DSL_OFFLINE=1 once, "
                      "or install requirements.txt into this environment from a local wheel directory.", file=sys.stderr)
                return 2
            print(f"Preparing isolated validator runtime: {target}", file=sys.stderr)
            # A failed or partial installation is repaired by a subsequent invocation.
            if not python.exists():
                venv.EnvBuilder(with_pip=True).create(target)
            elif not (target / "pyvenv.cfg").is_file():
                raise RuntimeError(f"{target} is not a virtual environment; select a separate runtime directory")
            pip_ready = subprocess.run([str(python), "-m", "pip", "--version"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if pip_ready.returncode != 0:
                subprocess.run([str(python), "-m", "ensurepip", "--upgrade"],
                               stdout=sys.stderr, stderr=sys.stderr, check=True)
            subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                            "-r", str(requirements)], stdout=sys.stderr, stderr=sys.stderr, check=True)
            if not usable(python):
                raise RuntimeError("Installed runtime failed its PyYAML check")
        if setup_only:
            print(f"Validator runtime ready: {python}")
            return 0
        return subprocess.run([str(python), str(ROOT / "scripts" / "validate_dsl.py"), *args], check=False).returncode
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"Could not prepare or run the validator: {exc}\n"
              "Check Python venv/pip availability, network access, and write access to DIFY_DSL_VENV_DIR. "
              "For offline installation, use pip --no-index --find-links <wheel-directory> -r requirements.txt "
              "inside that environment, then retry.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
