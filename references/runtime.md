# Validator runtime

Use Python 3.10 or newer from any directory:

```bash
python3 /path/to/dify-workflow-dsl/scripts/run_validator.py --strict --dify-version 1.18 workflow.yml
```

The first invocation creates an isolated virtual environment and installs the
runtime `requirements.txt`. Later invocations reuse it. Installation messages go
to stderr so `--format json` stdout stays machine-readable. A failed dependency
installation returns exit code 2 with recovery instructions; rerun after fixing
network or filesystem access. Validation errors return 1; success returns 0.
If an interrupted virtual environment has no pip, the runner restores it with
Python's bundled `ensurepip` before installing requirements. An unprepared
interpreter directory without `pyvenv.cfg` is rejected; choose a separate venv
directory instead.

The default cache is `$XDG_CACHE_HOME/dify-workflow-dsl/` or
`~/.cache/dify-workflow-dsl/`, keyed by Python major/minor and requirements content.
Set `DIFY_DSL_VENV_DIR` to use a specific directory. Use a separate directory per
Python version. This is a runtime cache, not a Dify server environment.

`bash install.sh --platform codex --setup` copies the runtime requirements and
prepares this cache. Other supported installation platforms use the same runner.
Without `--setup`, preparation happens on first validation. Set `DIFY_DSL_PYTHON`
when using the installer to select a Python executable. Manual invocation selects
Python directly (`python3.13 scripts/run_validator.py ...`).
Install targets must be separate from the source directory, its parents, and
its managed resource directories. The installer resolves directory symlinks
before checking this constraint, including when `--force` is used.

## Offline setup

Download wheels on a machine matching the offline machine's Python/platform:

```bash
python3 -m pip download -r requirements.txt --dest wheels
```

Copy the skill and wheels, then create and populate the selected environment:

```bash
export DIFY_DSL_VENV_DIR=/path/to/validator-venv
python3 -m venv "$DIFY_DSL_VENV_DIR"
"$DIFY_DSL_VENV_DIR/bin/python" -m pip install --no-index --find-links wheels -r requirements.txt
DIFY_DSL_OFFLINE=1 python3 scripts/run_validator.py --strict --dify-version 1.18 workflow.yml
```

On Windows, the environment interpreter is `Scripts/python.exe` instead of
`bin/python`. `DIFY_DSL_OFFLINE=1` prevents the runner from creating or downloading
an unprepared runtime. With an already prepared environment, it runs normally.

For managed environments, install `requirements.txt` yourself and invoke
`scripts/validate_dsl.py` directly. `requirements-dev.txt` includes the runtime
requirements; the test suite uses Python's standard `unittest` library.

The source-backed gate is separate: run `validate_with_dify_source.py` with the
target Dify API environment and its locked dependencies. Dify 1.18 uses Python
3.13; Dify 1.16 uses Python 3.12.
