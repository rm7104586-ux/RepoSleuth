"""
Entry Point Detector for RepoSleuth.
Identifies potential application starting files using structural heuristics,
naming patterns, and AST inspection. Provides clear, pedagogical explanations.
"""

import ast
from pathlib import Path
from typing import Dict, List, Any


COMMON_ENTRY_NAMES = {
    'manage.py': {
        'framework': 'Django',
        'confidence': 'High',
        'role': 'Django Management Script',
        'description': 'Standard entry script for Django web applications. Used for launching the development server, applying database migrations, and running management commands.'
    },
    'main.py': {
        'framework': 'Python / Generic',
        'confidence': 'High',
        'role': 'Standard Main Script',
        'description': 'Conventional primary entry point for Python console, utility, or modular backend applications.'
    },
    'app.py': {
        'framework': 'Flask / FastAPI / Streamlit',
        'confidence': 'High',
        'role': 'Web Application Root',
        'description': 'Standard application factory or entry module commonly used in Flask, FastAPI, Streamlit, and Bottle web frameworks.'
    },
    'run.py': {
        'framework': 'Generic / Runner',
        'confidence': 'High',
        'role': 'Application Runner Script',
        'description': 'Conventional startup runner script used to invoke development servers or trigger application loops.'
    },
    'server.py': {
        'framework': 'Backend / Server',
        'confidence': 'High',
        'role': 'Server Bootstrap Script',
        'description': 'Common entry point for setting up HTTP sockets, ASGI/WSGI servers, or background worker processes.'
    },
    'wsgi.py': {
        'framework': 'WSGI Server (Gunicorn/uWSGI)',
        'confidence': 'High',
        'role': 'WSGI Gateway Entry Point',
        'description': 'Production Web Server Gateway Interface entry point used by production web servers like Gunicorn and uWSGI.'
    },
    'asgi.py': {
        'framework': 'ASGI Server (Uvicorn/Daphne)',
        'confidence': 'High',
        'role': 'ASGI Asynchronous Gateway',
        'description': 'Asynchronous Server Gateway Interface entry point for async Python web applications and WebSockets.'
    },
    'cli.py': {
        'framework': 'CLI Application',
        'confidence': 'Medium',
        'role': 'Command-Line Interface Entry',
        'description': 'Dedicated command-line utility entry script providing terminal command arguments and sub-commands.'
    },
    '__main__.py': {
        'framework': 'Python Package Executable',
        'confidence': 'High',
        'role': 'Executable Package Entry',
        'description': 'Allows the directory/package to be executed directly from terminal via "python -m <package_name>".'
    },
    'setup.py': {
        'framework': 'Packaging / Distribution',
        'confidence': 'Medium',
        'role': 'Package Build & Install Script',
        'description': 'Traditional Python packaging script for building, installing, and distributing software modules.'
    }
}


class EntryPointVisitor(ast.NodeVisitor):
    """AST Visitor that searches for entry point markers like if __name__ == '__main__'."""

    def __init__(self):
        self.has_main_block = False
        self.main_block_line = None
        self.frameworks_detected = []
        self.cli_detected = False
        self.cli_line = None

    def visit_If(self, node: ast.If):
        # Look for: if __name__ == '__main__':
        test = node.test
        if isinstance(test, ast.Compare):
            left = test.left
            if isinstance(left, ast.Name) and left.id == '__name__':
                for op, comp in zip(test.ops, test.comparators):
                    if isinstance(op, ast.Eq) and isinstance(comp, ast.Constant) and comp.value == '__main__':
                        self.has_main_block = True
                        self.main_block_line = node.lineno
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detect Flask('...'), FastAPI(), ArgumentParser()
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr

        if name == 'Flask':
            self.frameworks_detected.append(('Flask', node.lineno))
        elif name == 'FastAPI':
            self.frameworks_detected.append(('FastAPI', node.lineno))
        elif name == 'ArgumentParser':
            self.cli_detected = True
            self.cli_line = node.lineno

        self.generic_visit(node)


def detect_entry_points(root_dir: str, python_files: List[str]) -> List[Dict[str, Any]]:
    """
    Scans project Python files to detect likely entry points and explain why.

    Returns:
        List of entry point objects sorted by confidence (High -> Medium -> Low).
    """
    root_path = Path(root_dir)
    detected_entries: List[Dict[str, Any]] = []
    seen_files = set()

    for rel_path in python_files:
        norm_path = rel_path.replace('\\', '/')
        file_path = root_path / norm_path
        filename = file_path.name.lower()

        reasons = []
        confidence = 'Low'
        framework = 'Python'
        role = 'Candidate Entry Point'
        line_reference = None
        snippet = ""

        # 1. Filename heuristic
        if filename in COMMON_ENTRY_NAMES:
            meta = COMMON_ENTRY_NAMES[filename]
            confidence = meta['confidence']
            framework = meta['framework']
            role = meta['role']
            reasons.append(meta['description'])

        # 2. AST inspection
        if file_path.is_file():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(file_path))
                visitor = EntryPointVisitor()
                visitor.visit(tree)

                if visitor.has_main_block:
                    confidence = 'High'
                    line_reference = visitor.main_block_line
                    reasons.append(
                        f"Contains the standard entry block 'if __name__ == \"__main__\":' on line {visitor.main_block_line}, allowing execution directly from the command line."
                    )
                    # Extract small snippet
                    lines = content.splitlines()
                    if visitor.main_block_line and visitor.main_block_line <= len(lines):
                        start = max(0, visitor.main_block_line - 1)
                        snippet_lines = lines[start:min(len(lines), start + 4)]
                        snippet = "\n".join(snippet_lines)

                for fw, fw_line in visitor.frameworks_detected:
                    confidence = 'High'
                    framework = fw
                    reasons.append(f"Instantiates a {fw} web application object on line {fw_line}.")

                if visitor.cli_detected:
                    if confidence != 'High':
                        confidence = 'Medium'
                    reasons.append(f"Configures command-line argument parsing on line {visitor.cli_line}.")

            except (SyntaxError, ValueError):
                pass
            except Exception:
                pass

        if reasons:
            detected_entries.append({
                'file': norm_path,
                'filename': Path(norm_path).name,
                'confidence': confidence,
                'framework': framework,
                'role': role,
                'reasons': reasons,
                'summary_reason': " ".join(reasons),
                'line': line_reference,
                'snippet': snippet
            })
            seen_files.add(norm_path)

    # Sort: High confidence first, then Medium, then Low
    confidence_order = {'High': 0, 'Medium': 1, 'Low': 2}
    detected_entries.sort(key=lambda x: (confidence_order.get(x['confidence'], 3), x['file']))

    return detected_entries
