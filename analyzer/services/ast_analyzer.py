"""
Python AST Dependency Analyzer for RepoSleuth.
Parses Python source code into Abstract Syntax Trees to extract module imports,
resolve internal vs. external dependencies, and classify them as confirmed or estimated.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple, Optional

# Standard library module names (Python 3.10+)
STDLIB_MODULES: Set[str] = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else {
    'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections', 'concurrent',
    'contextlib', 'copy', 'csv', 'dataclasses', 'datetime', 'decimal', 'difflib',
    'enum', 'errno', 'functools', 'glob', 'hashlib', 'heapq', 'http', 'importlib',
    'inspect', 'io', 'itertools', 'json', 'logging', 'math', 'multiprocessing',
    'os', 'pathlib', 'pickle', 'platform', 'queue', 'random', 're', 'shutil',
    'signal', 'socket', 'sqlite3', 'ssl', 'stat', 'string', 'subprocess', 'sys',
    'tempfile', 'threading', 'time', 'traceback', 'typing', 'unittest', 'urllib',
    'uuid', 'warnings', 'weakref', 'zipfile'
}


class ImportVisitor(ast.NodeVisitor):
    """AST Visitor that collects all import statements and their source locations."""

    def __init__(self):
        self.imports: List[Dict[str, Any]] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append({
                'type': 'import',
                'module': alias.name,
                'asname': alias.asname,
                'level': 0,
                'line': node.lineno,
                'raw': f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module_name = node.module or ""
        for alias in node.names:
            self.imports.append({
                'type': 'from_import',
                'module': module_name,
                'name': alias.name,
                'asname': alias.asname,
                'level': node.level,  # 0 = absolute, 1+ = relative
                'line': node.lineno,
                'raw': f"from {'.' * node.level + module_name} import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
            })
        self.generic_visit(node)


def normalize_posix(path_str: str) -> str:
    """Standardizes path delimiters to POSIX style '/'."""
    return path_str.replace('\\', '/').strip('/')


def resolve_dependency_target(
    source_file_rel: str,
    import_info: Dict[str, Any],
    project_python_files: Set[str]
) -> Tuple[Optional[str], str]:
    """
    Attempts to resolve an imported module name to a specific file in the project.

    Returns:
        (target_file_rel, status) where:
        - target_file_rel: matching relative path in project or None
        - status: 'confirmed', 'estimated', 'stdlib', or 'external'
    """
    module = import_info.get('module', '')
    level = import_info.get('level', 0)
    source_path = Path(source_file_rel)
    source_dir = source_path.parent

    # Check for relative import (level > 0)
    if level > 0:
        # e.g. from . import utils or from ..sub import foo
        try:
            target_dir = source_dir
            for _ in range(level - 1):
                target_dir = target_dir.parent

            # Candidate 1: module.py
            if module:
                cand1 = normalize_posix(str(target_dir / f"{module.replace('.', '/')}.py"))
                cand2 = normalize_posix(str(target_dir / module.replace('.', '/') / "__init__.py"))
                if cand1 in project_python_files:
                    return cand1, 'confirmed'
                if cand2 in project_python_files:
                    return cand2, 'confirmed'
            else:
                # from . import something
                imported_name = import_info.get('name', '')
                cand1 = normalize_posix(str(target_dir / f"{imported_name}.py"))
                cand2 = normalize_posix(str(target_dir / imported_name / "__init__.py"))
                if cand1 in project_python_files:
                    return cand1, 'confirmed'
                if cand2 in project_python_files:
                    return cand2, 'confirmed'

            # If not exact match but relative in scope, classify as estimated
            estimated_path = normalize_posix(str(target_dir / (module or import_info.get('name', ''))))
            return estimated_path, 'estimated'
        except Exception:
            return None, 'estimated'

    # Absolute import (level == 0)
    top_module = module.split('.')[0] if module else import_info.get('name', '')

    # Check Standard Library
    if top_module in STDLIB_MODULES:
        return top_module, 'stdlib'

    # Check if target is a file in the project root or subpackage
    module_path_parts = module.split('.') if module else [import_info.get('name', '')]
    module_rel_path = "/".join(module_path_parts)

    candidate_file = f"{module_rel_path}.py"
    candidate_pkg = f"{module_rel_path}/__init__.py"

    # Direct match from project root
    for cand in [candidate_file, candidate_pkg]:
        if cand in project_python_files:
            return cand, 'confirmed'

    # Match relative to source file's directory (common in older or flat scripts)
    cand_local_file = normalize_posix(str(source_dir / candidate_file))
    cand_local_pkg = normalize_posix(str(source_dir / candidate_pkg))
    if cand_local_file in project_python_files:
        return cand_local_file, 'confirmed'
    if cand_local_pkg in project_python_files:
        return cand_local_pkg, 'confirmed'

    # Search if any project python file filename matches top_module.py
    matching_files = [f for f in project_python_files if Path(f).stem == top_module]
    if len(matching_files) == 1:
        return matching_files[0], 'confirmed'
    elif len(matching_files) > 1:
        # Ambiguous match across different directories -> estimated
        return matching_files[0], 'estimated'

    # Not standard library, not matched in project -> External Third-Party Library
    return top_module, 'external'


def analyze_codebase_dependencies(root_dir: str, python_files: List[str]) -> Dict[str, Any]:
    """
    Performs comprehensive AST-based dependency analysis for all Python files.

    Returns:
        Dict containing graph nodes, edges, external dependencies,
        and dependency count breakdowns.
    """
    root_path = Path(root_dir)
    py_files_set = {normalize_posix(f) for f in python_files}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    edge_keys: Set[str] = set()

    external_deps_count: Dict[str, Dict[str, Any]] = {}
    confirmed_count = 0
    estimated_count = 0

    # Add each Python file as a node in the graph
    for py_file in sorted(py_files_set):
        nodes.append({
            'id': py_file,
            'label': Path(py_file).name,
            'path': py_file,
            'group': 'project_file',
            'title': f"Project File: {py_file}"
        })

    # Parse each file
    for py_file in py_files_set:
        full_path = root_path / py_file
        if not full_path.is_file():
            continue

        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                source_code = f.read()
            tree = ast.parse(source_code, filename=str(full_path))
        except (SyntaxError, ValueError):
            # Syntax errors will be captured by issue detector; skip AST import traversal
            continue
        except Exception:
            continue

        visitor = ImportVisitor()
        visitor.visit(tree)

        for imp in visitor.imports:
            target, status = resolve_dependency_target(py_file, imp, py_files_set)

            if status == 'stdlib':
                # We skip stdlib from project graph to prevent visual clutter,
                # but could track if desired.
                continue

            elif status == 'external':
                ext_name = target or "unknown"
                if ext_name not in external_deps_count:
                    external_deps_count[ext_name] = {'package': ext_name, 'count': 0, 'files': set()}
                external_deps_count[ext_name]['count'] += 1
                external_deps_count[ext_name]['files'].add(py_file)

            elif status in ('confirmed', 'estimated') and target:
                edge_key = f"{py_file}->{target}"
                if edge_key not in edge_keys:
                    edge_keys.add(edge_key)

                    if status == 'confirmed':
                        confirmed_count += 1
                    else:
                        estimated_count += 1

                    edges.append({
                        'from': py_file,
                        'to': target,
                        'status': status,
                        'label': imp['raw'],
                        'line': imp['line'],
                        'dashes': (status == 'estimated'),
                    })

    # Format external dependencies
    sorted_externals = sorted(
        [
            {
                'package': data['package'],
                'count': data['count'],
                'files': sorted(list(data['files']))
            }
            for data in external_deps_count.values()
        ],
        key=lambda x: x['count'],
        reverse=True
    )

    return {
        'nodes': nodes,
        'edges': edges,
        'external_dependencies': sorted_externals,
        'confirmed_count': confirmed_count,
        'estimated_count': estimated_count,
        'total_dependencies': confirmed_count + estimated_count,
        'total_external_packages': len(sorted_externals)
    }
