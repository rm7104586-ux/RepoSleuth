"""
Helper script to generate a sample project ZIP for RepoSleuth testing.
"""

import os
import zipfile
from pathlib import Path

sample_files = {
    'demo_library_app/app.py': '''"""
Flask Application Entry Point
"""
from flask import Flask, jsonify
from services.catalog import CatalogService
from config import APP_PORT, DEBUG_MODE

app = Flask(__name__)
catalog_service = CatalogService()

@app.route('/books')
def get_books():
    # TODO: Implement pagination for large library datasets
    return jsonify(catalog_service.list_books())

if __name__ == '__main__':
    print("Starting Demo Library Application...")
    app.run(port=APP_PORT, debug=DEBUG_MODE)
''',

    'demo_library_app/main.py': '''"""
CLI Application Runner
"""
import sys
import argparse
from services.catalog import CatalogService
from utils.helpers import format_book_display

def main():
    parser = argparse.ArgumentParser(description="Library Command Line Utility")
    parser.add_argument('--list', action='store_true', help="List all catalog books")
    args = parser.parse_args()

    service = CatalogService()
    if args.list:
        for book in service.list_books():
            print(format_book_display(book))
    else:
        # FIXME: Add interactive prompt if no CLI flags are supplied
        print("Use --list to view books.")

if __name__ == '__main__':
    main()
''',

    'demo_library_app/config.py': '''"""
Application Configuration
"""
import os

APP_PORT = int(os.environ.get('PORT', 5000))
DEBUG_MODE = True
SECRET_KEY = "demo-secret-key-for-sleuth"
# TODO: Store sensitive secrets in environment variables
''',

    'demo_library_app/models/__init__.py': '''"""Models Package"""
''',

    'demo_library_app/models/book.py': '''"""
Book Data Model
"""
from dataclasses import dataclass

@dataclass
class Book:
    id: int
    title: str
    author: str
    isbn: str
    is_borrowed: bool = False

    def toggle_borrow(self) -> None:
        self.is_borrowed = not self.is_borrowed
''',

    'demo_library_app/services/__init__.py': '''"""Services Package"""
''',

    'demo_library_app/services/catalog.py': '''"""
Catalog Business Logic Service
"""
import requests
from models.book import Book
from utils.helpers import validate_isbn

class CatalogService:
    def __init__(self):
        self.books = [
            Book(1, "The Pragmatic Programmer", "Andy Hunt", "978-0201616224"),
            Book(2, "Clean Code", "Robert C. Martin", "978-0132350884"),
            Book(3, "Design Patterns", "Gang of Four", "978-0201633610"),
        ]

    def list_books(self):
        return [b.__dict__ for b in self.books]

    def add_book(self, title: str, author: str, isbn: str):
        # FIXME: Check for duplicate ISBN before inserting
        if not validate_isbn(isbn):
            raise ValueError("Invalid ISBN format.")
        new_id = len(self.books) + 1
        book = Book(new_id, title, author, isbn)
        self.books.append(book)
        return book
''',

    'demo_library_app/services/empty_module.py': '''
''',

    'demo_library_app/utils/__init__.py': '''"""Utility Package"""
''',

    'demo_library_app/utils/helpers.py': '''"""
Helper and Utility Functions
"""
import re

def format_book_display(book_dict: dict) -> str:
    status = "[BORROWED]" if book_dict.get('is_borrowed') else "[AVAILABLE]"
    return f"{status} #{book_dict.get('id')}: {book_dict.get('title')} by {book_dict.get('author')}"

def validate_isbn(isbn_str: str) -> bool:
    clean = re.sub(r'[-\s]', '', isbn_str)
    return len(clean) in (10, 13)
''',

    'demo_library_app/tests/__init__.py': '''"""Tests Package"""
''',

    'demo_library_app/tests/test_catalog.py': '''"""
Unit Tests for Catalog Service
"""
import unittest
from services.catalog import CatalogService

class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.service = CatalogService()

    def test_list_books(self):
        books = self.service.list_books()
        self.assertEqual(len(books), 3)

if __name__ == '__main__':
    unittest.main()
''',

    'demo_library_app/tests/sample_broken_syntax.py': '''"""
Intentional syntax error for testing AST issue detection
"""
def broken_calculator():
    # Intentionally missing parenthesis and colon
    if True
        print "Missing colon and parenthesis"
''',

    'demo_library_app/README.md': '''# Demo Library Application
A sample Python application with Flask endpoints, CLI interface, dataclass models, and business logic.
'''
}


def build_demo_zip():
    target_zip = Path('sample_projects/demo_library_app.zip')
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arcname, content in sample_files.items():
            zf.writestr(arcname, content)
    print(f"Created sample project ZIP at: {target_zip.resolve()} (Size: {target_zip.stat().st_size} bytes)")


if __name__ == '__main__':
    build_demo_zip()
