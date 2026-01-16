#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import shutil
import subprocess


JS_SUFFIXES = {".js", ".mjs", ".cjs"}


def find_node_binary() -> str | None:
    """Find a usable Node.js binary."""
    str_candidates = [
        "/usr/local/bin/node",
        "/opt/homebrew/bin/node",
        "/usr/bin/node",
        "/usr/bin/nodejs",
    ]

    path_candidates = [
        Path.home()
        / "Library"
        / "Application Support"
        / "com.conductor.app"
        / "bin"
        / "node",
    ]

    for candidate in str_candidates:
        result = shutil.which(candidate)
        if result:
            return result

    for candidate in path_candidates:
        if candidate.exists():
            return str(candidate)

    return shutil.which("node") or shutil.which("nodejs")


def iter_js_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in JS_SUFFIXES
        and "node_modules" not in path.parts
    ]


def main(argv: list[str]) -> int:
    node = find_node_binary()
    if node is None:
        print("Node.js not available; skipping JS syntax check.", file=sys.stderr)
        return 0

    root = Path(__file__).resolve().parents[1]
    files = [Path(arg).resolve() for arg in argv[1:]]
    if not files:
        files = iter_js_files(root / "js") + iter_js_files(
            root / "src" / "fh_pydantic_form" / "assets"
        )

    failed = False
    for path in files:
        if path.suffix not in JS_SUFFIXES:
            continue
        if not path.exists():
            continue
        result = subprocess.run(
            [node, "--check", str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            failed = True
            sys.stderr.write(f"JavaScript syntax error in {path}:\n")
            if result.stderr:
                sys.stderr.write(result.stderr)
            if result.stdout:
                sys.stderr.write(result.stdout)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
