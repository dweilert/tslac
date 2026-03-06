#!/usr/bin/env python3
"""
Generate requirements files by scanning Python imports in the repository.

Creates:
  - requirements.txt        (runtime deps)
  - requirements-dev.txt    (runtime + dev tools)

Usage:
  python tools/generate_requirements.py
  python tools/generate_requirements.py --pin
  python tools/generate_requirements.py --check
  python tools/generate_requirements.py --pin --check

Notes:
- This scans *.py files and extracts top-level imports using AST (no regex).
- It filters out standard library modules and local project modules.
- It maps common import-name != package-name cases (PIL->Pillow, etc).
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from importlib import metadata as importlib_metadata  # py3.8+
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore[no-redef]


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "artifacts",
    "build",
    "dist",
}

# If your repo has a top-level package folder, add it here if needed.
# Otherwise "local module detection" below will catch it via filesystem checks.
LOCAL_IMPORT_PREFIXES = {
    # Example: "tslac",
}

# Dev tools you said you use
DEV_TOOLS = {
    "ruff",
    "black",
    "vulture",
    "pytest",
    "coverage",
}

# Common import name -> pip/conda package name mappings
IMPORT_TO_PACKAGE = {
    "bs4": "beautifulsoup4",
    "yaml": "PyYAML",
    "PIL": "Pillow",
    "dateutil": "python-dateutil",
    "googleapiclient": "google-api-python-client",
    "docx": "python-docx",
    "dotenv": "python-dotenv",
    "lxml": "lxml",
    "docx": "python-docx",
    "pypdf": "pypdf",
    "striprtf": "striprtf",
}

IGNORE_IMPORTS = {"importlib_metadata"}  # not needed on py3.12


@dataclass(frozen=True)
class ScanResult:
    runtime_packages: set[str]
    dev_packages: set[str]
    unknown_imports: set[str]  # imports we kept but can't resolve installed version for (optional)


# ------------------------------
# Helpers
# ------------------------------


def iter_py_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        out.append(p)
    return out


def extract_top_imports(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except Exception:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
    return imports


# Build once: all local module names based on repo files
def build_local_module_names(root: Path) -> set[str]:
    names: set[str] = set()

    for p in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue

        rel = p.relative_to(root)

        # module from file name
        if rel.name != "__init__.py":
            names.add(rel.stem)

        # package names from folder chain (a/b/c.py -> a, b, c)
        for part in rel.parts[:-1]:
            if part not in EXCLUDE_DIRS:
                names.add(part)

    return names


LOCAL_NAMES = build_local_module_names(PROJECT_ROOT)


def is_local_module(name: str) -> bool:
    return name in LOCAL_NAMES or name in LOCAL_IMPORT_PREFIXES


def is_stdlib(name: str) -> bool:
    # Python 3.10+: best method
    std = getattr(sys, "stdlib_module_names", None)
    if std and name in std:
        return True

    # Fallback heuristic: if import resolves and doesn't live in site-packages, probably stdlib
    try:
        import importlib.util

        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            return False
        origin = spec.origin.replace("\\", "/")
        if "/site-packages/" in origin or "/dist-packages/" in origin:
            return False
        return True
    except Exception:
        return False


def normalize_package(import_name: str) -> str:
    return IMPORT_TO_PACKAGE.get(import_name, import_name)


def installed_version(pkg_name: str) -> str | None:
    """Return installed version if pkg_name is installed (by distribution name)."""
    try:
        return importlib_metadata.version(pkg_name)
    except Exception:
        # Some distributions use different names than we have. Try common alternates.
        alternates = {
            "beautifulsoup4": ["bs4"],
            "PyYAML": ["yaml"],
            "Pillow": ["PIL"],
            "python-dateutil": ["dateutil"],
            "google-api-python-client": ["googleapiclient"],
        }
        for alt in alternates.get(pkg_name, []):
            try:
                return importlib_metadata.version(alt)
            except Exception:
                continue
        return None


def write_requirements(path: Path, pkgs: set[str], pin: bool, unknown: set[str]) -> None:
    lines: list[str] = []
    for pkg in sorted(pkgs, key=str.lower):
        if pin:
            ver = installed_version(pkg)
            if ver:
                lines.append(f"{pkg}=={ver}")
            else:
                unknown.add(pkg)
                lines.append(pkg)
        else:
            lines.append(pkg)

    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def scan_repo(check: bool) -> ScanResult:
    runtime: set[str] = set()
    dev: set[str] = set()
    unknown_imports: set[str] = set()

    for p in iter_py_files(PROJECT_ROOT):
        for imp in extract_top_imports(p):
            if not imp or imp.startswith("_"):
                continue
            if is_stdlib(imp):
                continue
            if is_local_module(imp):
                continue

            pkg = normalize_package(imp)

            # dev tools go to dev requirements
            if pkg in DEV_TOOLS:
                dev.add(pkg)
            else:
                runtime.add(pkg)

            if check:
                # In check mode, warn about things that aren't installed right now
                if installed_version(pkg) is None:
                    unknown_imports.add(pkg)

    # dev requirements should include runtime too (we’ll handle that on write)
    dev |= DEV_TOOLS

    return ScanResult(runtime_packages=runtime, dev_packages=dev, unknown_imports=unknown_imports)


# ------------------------------
# CLI
# ------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pin", action="store_true", help="Pin versions based on installed packages in this env"
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Report packages that appear in code but aren't installed",
    )
    args = ap.parse_args()

    res = scan_repo(check=args.check)

    unknown_runtime: set[str] = set()
    unknown_dev: set[str] = set()

    req = PROJECT_ROOT / "requirements.txt"
    req_dev = PROJECT_ROOT / "requirements-dev.txt"

    write_requirements(req, res.runtime_packages, pin=args.pin, unknown=unknown_runtime)

    # dev file includes runtime + dev tools
    dev_pkgs = set(res.runtime_packages) | set(res.dev_packages)
    write_requirements(req_dev, dev_pkgs, pin=args.pin, unknown=unknown_dev)

    print(f"Wrote: {req}")
    print(f"Wrote: {req_dev}")

    if args.check:
        missing = sorted(res.unknown_imports, key=str.lower)
        if missing:
            print("\nPackages referenced in code but not found installed in this environment:")
            for m in missing:
                print(f"  - {m}")
            print("\n(If your env is corrupted, this list may be large until you reinstall.)")
        else:
            print("\nAll detected packages appear to be installed.")

    if args.pin:
        if unknown_runtime or unknown_dev:
            all_unknown = sorted(unknown_runtime | unknown_dev, key=str.lower)
            if all_unknown:
                print("\nCould not determine versions for:")
                for u in all_unknown:
                    print(f"  - {u}")
                print(
                    "\nThese were left unpinned. This is normal if the distribution name differs."
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
