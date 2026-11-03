"""
File Explorer Service for RepoSleuth.
Builds directory trees, calculates lines of code and file metrics,
and provides safe file viewing.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

EXTENSION_LANGUAGE_MAP = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.jsx': 'React JSX',
    '.tsx': 'React TSX',
    '.html': 'HTML',
    '.htm': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.json': 'JSON',
    '.md': 'Markdown',
    '.txt': 'Text',
    '.sql': 'SQL',
    '.yml': 'YAML',
    '.yaml': 'YAML',
    '.xml': 'XML',
    '.sh': 'Shell',
    '.bat': 'Batch',
    '.ps1': 'PowerShell',
    '.toml': 'TOML',
    '.ini': 'INI',
    '.cfg': 'Config',
}

IGNORED_NAMES = {
    '__pycache__', '.git', '.svn', '.hg', '.DS_Store', 'Thumbs.db',
    '.venv', 'venv', 'env', 'node_modules', '.idea', '.vscode', '.pytest_cache'
}


def format_bytes(bytes_val: int) -> str:
    """Formats raw byte count into human-friendly string."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.2f} MB"


def count_file_lines(file_path: Path) -> int:
    """Safely counts number of lines in a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def build_file_tree_and_metrics(root_dir: str) -> Dict[str, Any]:
    """
    Traverses the extracted codebase directory and returns:
    - Hierarchical tree structure (for frontend tree explorer)
    - Total files count
    - Total folders count
    - Total size in bytes
    - Total lines of code
    - Breakdown by language
    - Flat list of all Python files (relative paths)
    """
    root_path = Path(root_dir)
    if not root_path.is_dir():
        return {
            'tree': [],
            'total_files': 0,
            'total_folders': 0,
            'total_size': 0,
            'total_lines': 0,
            'languages': {},
            'python_files': [],
        }

    total_files = 0
    total_folders = 0
    total_size = 0
    total_lines = 0
    languages: Dict[str, Dict[str, int]] = {}
    python_files: List[str] = []

    def _traverse_dir(current_dir: Path, rel_prefix: str = "") -> List[Dict[str, Any]]:
        nonlocal total_files, total_folders, total_size, total_lines

        nodes: List[Dict[str, Any]] = []

        try:
            entries = sorted(list(current_dir.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return nodes

        for entry in entries:
            if entry.name in IGNORED_NAMES or entry.name.startswith('.'):
                continue

            rel_path = f"{rel_prefix}/{entry.name}" if rel_prefix else entry.name

            if entry.is_dir():
                total_folders += 1
                children = _traverse_dir(entry, rel_path)
                nodes.append({
                    'name': entry.name,
                    'path': rel_path,
                    'type': 'folder',
                    'children': children,
                    'child_count': len(children)
                })
            elif entry.is_file():
                total_files += 1
                try:
                    file_size = entry.stat().st_size
                except OSError:
                    file_size = 0
                total_size += file_size

                ext = entry.suffix.lower()
                lang = EXTENSION_LANGUAGE_MAP.get(ext, 'Other')
                lines = 0

                # Count lines for code/text files (< 2MB)
                if file_size < 2 * 1024 * 1024:
                    lines = count_file_lines(entry)
                    total_lines += lines

                if ext == '.py':
                    python_files.append(rel_path)

                if lang not in languages:
                    languages[lang] = {'files': 0, 'lines': 0, 'bytes': 0}
                languages[lang]['files'] += 1
                languages[lang]['lines'] += lines
                languages[lang]['bytes'] += file_size

                nodes.append({
                    'name': entry.name,
                    'path': rel_path,
                    'type': 'file',
                    'extension': ext,
                    'language': lang,
                    'size': file_size,
                    'formatted_size': format_bytes(file_size),
                    'lines': lines
                })

        return nodes

    tree = _traverse_dir(root_path)

    return {
        'tree': tree,
        'total_files': total_files,
        'total_folders': total_folders,
        'total_size': total_size,
        'total_lines': total_lines,
        'languages': languages,
        'python_files': python_files,
    }


def read_project_file_content(root_dir: str, rel_path: str, max_bytes: int = 500 * 1024) -> Dict[str, Any]:
    """
    Safely reads a project file's content for the in-browser viewer.
    Validates path containment to prevent directory traversal.
    """
    root_path = Path(root_dir).resolve()
    target_path = (root_path / rel_path).resolve()

    if not target_path.is_relative_to(root_path):
        return {
            'success': False,
            'error': 'Access denied: Invalid file path outside codebase directory.'
        }

    if not target_path.is_file():
        return {
            'success': False,
            'error': f'File not found: {rel_path}'
        }

    file_size = target_path.stat().st_size
    if file_size > max_bytes:
        return {
            'success': False,
            'error': f'File is too large to preview directly ({format_bytes(file_size)} > {format_bytes(max_bytes)}).'
        }

    try:
        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        ext = target_path.suffix.lower()
        lang = EXTENSION_LANGUAGE_MAP.get(ext, 'plaintext')

        numbered_lines = [
            {'line_num': idx + 1, 'text': line.rstrip('\r\n')}
            for idx, line in enumerate(lines)
        ]

        return {
            'success': True,
            'file_name': target_path.name,
            'rel_path': rel_path,
            'language': lang,
            'extension': ext,
            'total_lines': len(lines),
            'size': file_size,
            'formatted_size': format_bytes(file_size),
            'lines': numbered_lines,
            'raw_content': "".join(lines)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unable to read file: {str(e)}'
        }
