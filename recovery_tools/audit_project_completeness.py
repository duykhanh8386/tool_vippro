"""Static-only import/dependency graph audit for recovered_project.

Parses source with AST. It never imports or executes recovered modules.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path


def module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or "<root>"


def resolve_relative(current: str, is_package: bool, level: int, target: str | None) -> str:
    if level == 0:
        return target or ""
    package = current if is_package else current.rpartition(".")[0]
    parts = package.split(".") if package else []
    if level > 1:
        parts = parts[: -(level - 1)] if level - 1 <= len(parts) else []
    if target:
        parts.extend(target.split("."))
    return ".".join(parts)


def inside_try(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    cursor = node
    while cursor in parents:
        cursor = parents[cursor]
        if isinstance(cursor, ast.Try):
            return True
    return False


def tarjan(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    low: dict[str, int] = {}
    result: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for nxt in graph.get(node, set()):
            if nxt not in graph:
                continue
            if nxt not in indexes:
                visit(nxt)
                low[node] = min(low[node], low[nxt])
            elif nxt in on_stack:
                low[node] = min(low[node], indexes[nxt])
        if low[node] == indexes[node]:
            component = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            if len(component) > 1 or node in graph.get(node, set()):
                result.append(sorted(component))

    for node in graph:
        if node not in indexes:
            visit(node)
    return sorted(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    paths = [
        path
        for path in sorted(root.rglob("*.py"))
        if not any(part.startswith(".venv") for part in path.relative_to(root).parts)
    ]
    modules = {module_name(root, path): path for path in paths}
    packages = {name for name, path in modules.items() if path.name == "__init__.py"}
    trees = {
        name: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, path in modules.items()
    }
    exports: dict[str, set[str]] = {}
    for name, tree in trees.items():
        names: set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name != "*":
                        names.add(alias.asname or alias.name.split(".")[0])
        exports[name] = names
    graph: dict[str, set[str]] = {name: set() for name in modules}
    records: list[dict[str, object]] = []
    third_party_locations: dict[str, set[str]] = defaultdict(set)

    for current, path in modules.items():
        tree = trees[current]
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            imports: list[tuple[str, int]] = []
            if isinstance(node, ast.Import):
                imports = [(alias.name, 0) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = resolve_relative(current, current in packages, node.level, node.module)
                imports = [(base, node.level)]
            else:
                continue
            for imported, level in imports:
                top = imported.split(".")[0] if imported else ""
                if imported in modules or imported in packages:
                    kind, resolved = "local", True
                    graph[current].add(imported)
                elif top in {"src", "web"}:
                    kind, resolved = "missing_local", False
                elif top in sys.stdlib_module_names:
                    kind, resolved = "stdlib", True
                else:
                    kind, resolved = "third_party", None
                    third_party_locations[top].add(str(path.relative_to(root)).replace("\\", "/"))
                records.append(
                    {
                        "source": str(path.relative_to(root)).replace("\\", "/"),
                        "source_module": current,
                        "line": node.lineno,
                        "import": imported,
                        "kind": kind,
                        "resolved": resolved,
                        "optional_try": inside_try(node, parents),
                        "names": [alias.name for alias in node.names]
                        if isinstance(node, ast.ImportFrom)
                        else [],
                    }
                )

    missing_symbols = []
    for record in records:
        if record["kind"] != "local":
            continue
        target = str(record["import"])
        for imported_name in record["names"]:
            if imported_name == "*":
                continue
            submodule = f"{target}.{imported_name}"
            if imported_name not in exports.get(target, set()) and submodule not in modules:
                missing_symbols.append({**record, "missing_name": imported_name})

    output = {
        "python_files": len(paths),
        "modules": sorted(modules),
        "imports": records,
        "missing_local": [r for r in records if r["kind"] == "missing_local"],
        "missing_local_symbols": missing_symbols,
        "optional_imports": [r for r in records if r["optional_try"]],
        "third_party": {key: sorted(value) for key, value in sorted(third_party_locations.items())},
        "cycles": tarjan(graph),
        "local_graph": {key: sorted(value) for key, value in sorted(graph.items()) if value},
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
