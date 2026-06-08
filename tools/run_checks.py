#!/usr/bin/env python3
"""Run lightweight project checks without pytest or Home Assistant."""

from __future__ import annotations

import ast
import importlib.util
import json
import py_compile
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _run_test_functions() -> int:
    count = 0
    for test_path in sorted((ROOT / "tests").glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(test_path.stem, test_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {test_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            getattr(module, name)()
            count += 1
            print(f"PASS {test_path.name}::{name}")
    return count


def _validate_python() -> int:
    count = 0
    paths = [
        *(ROOT / "custom_components").rglob("*.py"),
        *(ROOT / "tests").rglob("*.py"),
        *(ROOT / "tools").rglob("*.py"),
    ]
    with tempfile.TemporaryDirectory() as output_dir:
        for path in paths:
            ast.parse(path.read_text())
            py_compile.compile(
                str(path),
                cfile=str(Path(output_dir) / f"{count}.pyc"),
                doraise=True,
            )
            count += 1
    print(f"PASS syntax and compile checks ({count} files)")
    return count


def _validate_json() -> int:
    paths = [
        *(ROOT / "custom_components").rglob("*.json"),
        ROOT / "hacs.json",
        *(ROOT / "tests" / "fixtures").glob("*.json"),
    ]
    for path in paths:
        json.loads(path.read_text())
    print(f"PASS JSON validation ({len(paths)} files)")
    return len(paths)


def main() -> int:
    try:
        tests = _run_test_functions()
        python_files = _validate_python()
        json_files = _validate_json()
    except Exception as err:
        print(f"FAIL {err}", file=sys.stderr)
        return 1
    print(
        f"\nAll checks passed: {tests} tests, "
        f"{python_files} Python files, {json_files} JSON files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
