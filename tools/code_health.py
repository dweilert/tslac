#!/usr/bin/env python3
"""
Repo code health tool:
  - dead imports: uses Ruff (best-in-class) if installed
  - unused files: import-reachability from entrypoints/tests
  - circular imports: detects cycles in local module import graph

Usage:
  python tools/code_health.py dead-imports
  python tools/code_health.py unused-files
  python tools/code_health.py cycles
  python tools/code_health.py all

Optional:
  python tools/code_health.py unused-files --write-rm artifacts/git-rm-unused.sh
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

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

# Treat these as "entrypoints" for reachability.
# Adjust if you change your boot pattern.
DEFAULT_ENTRYPOINTS = ["app.py", "run.py", "server.py"]

# If you have special "scripts/" or "bin/" entrypoints, add them here.
EXTRA_ROOT_GLOBS = [
    "tests/test_*.py",
]


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


def module_name_from_path(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT)
    parts = list(rel.parts)
    parts[-1] = parts[-1][:-3]  # strip .py
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def path_from_module_name(mod: str) -> Path | None:
    # Try file module
    p = PROJECT_ROOT / (mod.replace(".", os.sep) + ".py")
    if p.exists():
        return p
    # Try package module
    p = PROJECT_ROOT / (mod.replace(".", os.sep)) / "__init__.py"
    if p.exists():
        return p
    return None


def build_local_names(root: Path) -> set[str]:
    """All local top-level names (folders and .py stems) to help classify imports."""
    names: set[str] = set()
    for p in iter_py_files(root):
        rel = p.relative_to(root)
        # file stem at any level counts as a local name (helps with `import rules` etc.)
        if rel.name != "__init__.py":
            names.add(rel.stem)
        for part in rel.parts[:-1]:
            if part not in EXCLUDE_DIRS:
                names.add(part)
    return names


LOCAL_NAMES = build_local_names(PROJECT_ROOT)


def extract_top_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
    return imports


def extract_import_edges(path: Path) -> set[str]:
    """
    Return imported module strings as written (e.g. "watch.scan", "web.request").
    We'll later resolve to local modules where possible.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return set()

    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                out.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return out


def is_stdlib(name: str) -> bool:
    std = getattr(sys, "stdlib_module_names", None)
    if std and name in std:
        return True

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


def is_local_top(name: str) -> bool:
    return name in LOCAL_NAMES


def entrypoint_paths() -> list[Path]:
    paths: list[Path] = []
    for rel in DEFAULT_ENTRYPOINTS:
        p = PROJECT_ROOT / rel
        if p.exists():
            paths.append(p)

    for g in EXTRA_ROOT_GLOBS:
        paths.extend(sorted(PROJECT_ROOT.glob(g)))

    # De-dupe
    uniq: list[Path] = []
    seen = set()
    for p in paths:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq


# ------------------------------
# Unused files (import reachability)
# ------------------------------


@dataclass(frozen=True)
class UnusedFilesReport:
    reachable_modules: set[str]
    unused_files: list[Path]


def build_module_map() -> dict[str, Path]:
    return {module_name_from_path(p): p for p in iter_py_files(PROJECT_ROOT)}


def resolve_import_to_local_module(import_str: str, module_map: dict[str, Path]) -> set[str]:
    """
    Try to resolve an import string to local module(s).
    We resolve:
      - exact: "watch.scan" -> if exists
      - parent packages: "watch.scan" -> "watch"
    """
    out: set[str] = set()
    if import_str in module_map:
        out.add(import_str)

    parts = import_str.split(".")
    for i in range(len(parts) - 1, 0, -1):
        parent = ".".join(parts[:i])
        if parent in module_map:
            out.add(parent)

    # Also handle "import rules" where real module might be collect.rules, etc.
    # If top-level name matches a local file stem or folder, treat as local and let reachability find it.
    top = parts[0]
    if top in module_map:
        out.add(top)

    return out


def find_unused_files() -> UnusedFilesReport:
    module_map = build_module_map()

    # Build import adjacency for local modules
    adj: dict[str, set[str]] = {m: set() for m in module_map}
    for m, p in module_map.items():
        for imp in extract_import_edges(p):
            for resolved in resolve_import_to_local_module(imp, module_map):
                adj[m].add(resolved)

    roots = []
    for ep in entrypoint_paths():
        roots.append(module_name_from_path(ep))

    # BFS/DFS reachability
    seen: set[str] = set()
    stack = roots[:]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack.extend(sorted(adj.get(m, set())))

    unused_mods = sorted(set(module_map) - seen)
    unused_files = [module_map[m] for m in unused_mods]

    return UnusedFilesReport(reachable_modules=seen, unused_files=unused_files)


# ------------------------------
# Circular imports (cycle detection)
# ------------------------------


@dataclass(frozen=True)
class CyclesReport:
    cycles: list[list[str]]  # list of strongly connected components (size >= 2)


def tarjan_scc(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    idx: dict[str, int] = {}
    low: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        idx[v] = index
        low[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, set()):
            if w not in idx:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], idx[w])

        if low[v] == idx[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) >= 2:
                sccs.append(sorted(comp))

    for v in graph:
        if v not in idx:
            strongconnect(v)

    return sorted(sccs, key=lambda c: (len(c), c))


def find_cycles() -> CyclesReport:
    module_map = build_module_map()
    graph: dict[str, set[str]] = {m: set() for m in module_map}

    for m, p in module_map.items():
        for imp in extract_import_edges(p):
            for resolved in resolve_import_to_local_module(imp, module_map):
                # keep only local modules
                if resolved in module_map:
                    graph[m].add(resolved)

    cycles = tarjan_scc(graph)
    return CyclesReport(cycles=cycles)


# ------------------------------
# Dead imports (Ruff wrapper)
# ------------------------------


def run_dead_imports() -> int:
    """
    Dead imports are best handled by Ruff:
      - F401: imported but unused
      - F811: redefinition of unused name, etc (optional)
    """
    try:
        proc = subprocess.run(
            ["ruff", "check", ".", "--select", "F401"],
            cwd=str(PROJECT_ROOT),
            check=False,
        )
        return proc.returncode
    except FileNotFoundError:
        print("ruff is not installed in this environment.")
        print("Install with:  conda install -c conda-forge ruff   OR   pip install ruff")
        return 2


# ------------------------------
# CLI
# ------------------------------


def cmd_unused_files(write_rm: Path | None) -> int:
    rep = find_unused_files()
    if not rep.unused_files:
        print("No import-unreachable .py files found from entrypoints/tests.")
        return 0

    print("Import-unreachable Python files (review before deleting):")
    for p in rep.unused_files:
        print(f"  - {p.relative_to(PROJECT_ROOT)}")

    if write_rm:
        write_rm.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"git rm -f {p.relative_to(PROJECT_ROOT)}" for p in rep.unused_files]
        write_rm.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWrote removal script: {write_rm}")
    return 0


def cmd_cycles() -> int:
    rep = find_cycles()
    if not rep.cycles:
        print("No circular import cycles detected (SCC size >= 2).")
        return 0

    print("Circular import groups detected (Strongly Connected Components):")
    for comp in rep.cycles:
        print(f"\nCycle group ({len(comp)} modules):")
        for m in comp:
            print(f"  - {m}")
    return 0


def cmd_all(write_rm: Path | None) -> int:
    print("== Dead imports (ruff F401) ==")
    run_dead_imports()
    print("\n== Unused files (import reachability) ==")
    cmd_unused_files(write_rm=write_rm)
    print("\n== Circular imports (SCC) ==")
    cmd_cycles()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("dead-imports")

    p_unused = sub.add_parser("unused-files")
    p_unused.add_argument(
        "--write-rm", type=str, default=None, help="Write git-rm script to this path"
    )

    sub.add_parser("cycles")

    p_all = sub.add_parser("all")
    p_all.add_argument(
        "--write-rm", type=str, default=None, help="Write git-rm script to this path"
    )

    args = ap.parse_args()

    if args.cmd == "dead-imports":
        return run_dead_imports()

    if args.cmd == "unused-files":
        out = Path(args.write_rm) if args.write_rm else None
        return cmd_unused_files(write_rm=out)

    if args.cmd == "cycles":
        return cmd_cycles()

    if args.cmd == "all":
        out = Path(args.write_rm) if args.write_rm else None
        return cmd_all(write_rm=out)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
