"""
Code Issue Detector for RepoSleuth.
Detects:
1. Python Syntax Errors (AST parsing)
2. TODO and FIXME comment tags
3. Empty Python files
4. Unusually large source files (> 500 lines)
5. Wildcard imports (from module import *)
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any

TODO_FIXME_PATTERN = re.compile(r'#\s*(TODO|FIXME|BUG|HACK|XXX)\b[:\s]*(.*)', re.IGNORECASE)
LARGE_FILE_LINE_THRESHOLD = 500


def detect_code_issues(root_dir: str, python_files: List[str]) -> Dict[str, Any]:
    """
    Inspects all Python files in the extracted codebase for issues.

    Returns:
        Dict containing:
        - issues: List of issue dictionaries
        - counts: Dictionary with counts per category
        - health_score: Calculated score from 0 to 100
    """
    root_path = Path(root_dir)
    issues: List[Dict[str, Any]] = []

    counts = {
        'syntax_errors': 0,
        'todos_fixmes': 0,
        'empty_files': 0,
        'large_files': 0,
        'wildcard_imports': 0,
        'total': 0
    }

    for rel_path in python_files:
        norm_path = rel_path.replace('\\', '/')
        file_path = root_path / norm_path

        if not file_path.is_file():
            continue

        file_size = file_path.stat().st_size
        filename = file_path.name

        # 1. Empty File Detection
        if file_size == 0:
            is_init = (filename == '__init__.py')
            severity = 'Info' if is_init else 'Medium'
            counts['empty_files'] += 1
            issues.append({
                'category': 'empty_file',
                'severity': severity,
                'file': norm_path,
                'line': 1,
                'title': 'Empty File',
                'description': f"Empty package marker file ({filename})" if is_init else "Python file has 0 bytes and contains no code or logic.",
                'snippet': ""
            })
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            continue

        # Check if file has only whitespace
        if not content.strip():
            is_init = (filename == '__init__.py')
            severity = 'Info' if is_init else 'Medium'
            counts['empty_files'] += 1
            issues.append({
                'category': 'empty_file',
                'severity': severity,
                'file': norm_path,
                'line': 1,
                'title': 'Empty File (Whitespace only)',
                'description': f"Empty package marker file ({filename})" if is_init else "File contains only whitespace and has no executable code.",
                'snippet': ""
            })
            continue

        # 2. Large File Detection
        if len(lines) > LARGE_FILE_LINE_THRESHOLD:
            counts['large_files'] += 1
            issues.append({
                'category': 'large_file',
                'severity': 'Medium',
                'file': norm_path,
                'line': len(lines),
                'title': 'Oversized Source File',
                'description': f"File has {len(lines)} lines (exceeds recommended {LARGE_FILE_LINE_THRESHOLD} line threshold). Consider decomposing into smaller modules.",
                'snippet': f"# Total Lines: {len(lines)}"
            })

        # 3. TODO & FIXME Comments
        for idx, line in enumerate(lines, start=1):
            match = TODO_FIXME_PATTERN.search(line)
            if match:
                tag = match.group(1).upper()
                desc = match.group(2).strip() or "No additional description provided."
                severity = 'High' if tag in ('FIXME', 'BUG') else 'Low'
                counts['todos_fixmes'] += 1
                issues.append({
                    'category': 'todo_fixme',
                    'severity': severity,
                    'file': norm_path,
                    'line': idx,
                    'title': f"{tag} Item",
                    'description': desc,
                    'snippet': line.strip()
                })

        # 4. Syntax Error Detection (via AST)
        ast_tree = None
        try:
            ast_tree = ast.parse(content, filename=norm_path)
        except SyntaxError as syn_err:
            counts['syntax_errors'] += 1
            err_line = syn_err.lineno or 1
            err_col = syn_err.offset or 0
            err_text = syn_err.text.strip() if syn_err.text else ""

            issues.append({
                'category': 'syntax_error',
                'severity': 'High',
                'file': norm_path,
                'line': err_line,
                'column': err_col,
                'title': 'Python Syntax Error',
                'description': f"SyntaxError: {syn_err.msg} (line {err_line}, col {err_col})",
                'snippet': err_text
            })
        except Exception:
            pass

        # 5. Wildcard Imports Detection
        if ast_tree:
            for node in ast.walk(ast_tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == '*':
                            mod_name = node.module or ""
                            issues.append({
                                'category': 'wildcard_import',
                                'severity': 'Low',
                                'file': norm_path,
                                'line': node.lineno,
                                'title': 'Wildcard Import',
                                'description': f"Wildcard import 'from {mod_name} import *' pollutes the local namespace and conceals dependencies.",
                                'snippet': f"from {node.module} import *"
                            })

    counts['total'] = len(issues)

    # Calculate overall codebase health score (0 - 100)
    # Deductions:
    # - Each syntax error: -20
    # - Each empty file (excluding __init__): -5
    # - Each large file: -4
    # - Each FIXME: -5
    # - Each TODO: -1
    # - Each wildcard import: -2
    score = 100
    for issue in issues:
        cat = issue['category']
        sev = issue['severity']
        if cat == 'syntax_error':
            score -= 20
        elif cat == 'empty_file' and sev != 'Info':
            score -= 5
        elif cat == 'large_file':
            score -= 4
        elif cat == 'todo_fixme':
            score -= (5 if sev == 'High' else 1)
        elif cat == 'wildcard_import':
            score -= 2

    health_score = max(10, min(100, score))

    # Sort issues: High severity first, then Medium, then Low/Info
    severity_rank = {'High': 0, 'Medium': 1, 'Low': 2, 'Info': 3}
    issues.sort(key=lambda x: (severity_rank.get(x['severity'], 4), x['file'], x['line']))

    return {
        'issues': issues,
        'counts': counts,
        'health_score': health_score
    }
