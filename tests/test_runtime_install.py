from __future__ import annotations

import json
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]


class InstalledRuntimeTests(unittest.TestCase):
    def test_partial_runtime_repairs_missing_pip_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            venv.EnvBuilder(with_pip=False).create(runtime)
            python = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            env = dict(os.environ, DIFY_DSL_OFFLINE="0", DIFY_DSL_VENV_DIR=str(runtime),
                       PIP_NO_INDEX="1", PIP_FIND_LINKS="", PIP_CONFIG_FILE=os.devnull, PIP_NO_CACHE_DIR="1")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/run_validator.py"), "--setup"],
                                    env=env, capture_output=True, text=True)
            # No wheel source is supplied: dependency installation must fail cleanly,
            # but the interrupted venv must now have a working pip for the next retry.
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            pip = subprocess.run([str(python), "-m", "pip", "--version"], capture_output=True, text=True)
            self.assertEqual(0, pip.returncode, pip.stderr)
            self.assertIn("--find-links", result.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX interpreter link")
    def test_unprepared_non_venv_is_not_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            (runtime / "bin").mkdir()
            (runtime / "bin/python").symlink_to(sys.executable)
            from unittest.mock import patch
            sys.path.insert(0, str(ROOT / "scripts"))
            import run_validator
            with patch.object(run_validator, "usable", return_value=False), \
                 patch.dict(os.environ, DIFY_DSL_VENV_DIR=str(runtime), DIFY_DSL_OFFLINE="0"), \
                 patch.object(sys, "argv", ["run_validator.py", "--setup"]), \
                 patch.object(run_validator.subprocess, "run") as run, \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, run_validator.main())
                run.assert_not_called()
            self.assertFalse((runtime / "pyvenv.cfg").exists())

    @unittest.skipIf(os.name == "nt", "Bash installer test")
    def test_force_install_rejects_source_overlap(self):
        for placement in ("same", "alias", "parent", "managed-child"):
            with self.subTest(placement=placement), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "source"
                source.mkdir()
                shutil.copy2(ROOT / "install.sh", source / "install.sh")
                (source / "scripts").mkdir()
                marker = source / "scripts/marker.txt"
                marker.write_text("preserve source")
                (source / "SKILL.md").write_text("preserve skill")
                targets = {"same": source, "parent": source.parent,
                           "managed-child": source / "scripts/nested"}
                alias = source.parent / "alias"
                alias.symlink_to(source, target_is_directory=True)
                targets["alias"] = alias
                result = subprocess.run(["bash", str(source / "install.sh"), "--platform", "codex",
                                         "--target-dir", str(targets[placement]), "--force"],
                                        capture_output=True, text=True)
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertIn("Install target must not", result.stderr)
                self.assertEqual("preserve source", marker.read_text())
                self.assertEqual("preserve skill", (source / "SKILL.md").read_text())

    def test_offline_missing_runtime_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "missing-runtime"
            env = dict(os.environ, DIFY_DSL_OFFLINE="1", DIFY_DSL_VENV_DIR=str(target))
            result = subprocess.run([sys.executable, str(ROOT / "scripts/run_validator.py"), "--setup"],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(2, result.returncode)
            self.assertIn("local wheel", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(target.exists())

    @unittest.skipIf(os.name == "nt", "Bash installer test")
    def test_install_is_self_contained_and_reuses_offline_runtime(self):
        with tempfile.TemporaryDirectory(prefix="dify installed ") as directory:
            installed = Path(directory) / "skill with spaces"
            runtime = Path(sys.prefix)
            env = dict(os.environ, DIFY_DSL_OFFLINE="1", DIFY_DSL_VENV_DIR=str(runtime), DIFY_DSL_PYTHON=sys.executable)
            result = subprocess.run(["bash", str(ROOT / "install.sh"), "--platform", "opencode",
                                     "--target-dir", str(installed), "--setup"], env=env, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertTrue((installed / "requirements.txt").is_file())
            result = subprocess.run([sys.executable, str(installed / "scripts/run_validator.py"),
                                     "--strict", "--format", "json", "--dify-version", "1.18",
                                     str(installed / "examples/dify-1.18.0/02-agent-routes.yml")],
                                    cwd=directory, env=env, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual("valid", json.loads(result.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
