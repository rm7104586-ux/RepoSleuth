"""
Safe ZIP Extractor for RepoSleuth.
Guarantees security against Path Traversal (Zip Slip) and Zip Bomb attacks.
"""

import os
import zipfile
from pathlib import Path
from typing import Tuple, List, Dict, Any


# Configurable security limits
MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_SINGLE_FILE_BYTES = 20 * 1024 * 1024          # 20 MB
MAX_FILE_COUNT = 5000                             # Max files allowed in archive

IGNORED_DIRECTORY_NAMES = {
    '__pycache__', '.git', '.svn', '.hg', '.DS_Store', 'Thumbs.db',
    '.venv', 'venv', 'env', 'node_modules', '.idea', '.vscode', '.pytest_cache'
}


class ZipExtractionError(Exception):
    """Custom exception raised when ZIP validation or extraction fails."""
    pass


def is_safe_path(target_dir: Path, path: Path) -> bool:
    """
    Validates that a resolved path is strictly within the target directory.
    Prevents Zip Slip / path traversal attacks.
    """
    try:
        resolved_target = target_dir.resolve()
        resolved_path = path.resolve()
        return resolved_path.is_relative_to(resolved_target)
    except (ValueError, RuntimeError):
        return False


def should_skip_member(member_name: str) -> bool:
    """
    Returns True if the file or folder is an ignored artifact (cache, git, venv).
    """
    parts = Path(member_name).parts
    for part in parts:
        if part in IGNORED_DIRECTORY_NAMES or part.startswith('._'):
            return True
    return False


def safe_extract_zip(zip_path: str, destination_dir: str) -> Dict[str, Any]:
    """
    Safely inspects and extracts a ZIP archive into destination_dir.

    Args:
        zip_path: Path to the uploaded zip file on disk.
        destination_dir: Directory where files should be extracted.

    Returns:
        Dict containing extraction details:
        {
            'extracted_path': str,
            'file_count': int,
            'total_size': int,
            'skipped_count': int,
            'root_folder': str (if single top-level folder detected)
        }

    Raises:
        ZipExtractionError: If archive is invalid, malicious, or exceeds limits.
    """
    if not os.path.exists(zip_path):
        raise ZipExtractionError(f"ZIP file does not exist: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise ZipExtractionError("The uploaded file is not a valid ZIP archive.")

    dest_path = Path(destination_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    total_uncompressed_size = 0
    file_count = 0
    skipped_count = 0
    extracted_files: List[str] = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            infolist = zf.infolist()

            if not infolist:
                raise ZipExtractionError("The ZIP archive is empty.")

            if len(infolist) > MAX_FILE_COUNT:
                raise ZipExtractionError(
                    f"ZIP archive contains too many files ({len(infolist)} > {MAX_FILE_COUNT} limit)."
                )

            # Pre-extraction validation pass
            for info in infolist:
                # Security Check: Single file size
                if info.file_size > MAX_SINGLE_FILE_BYTES:
                    raise ZipExtractionError(
                        f"File '{info.filename}' exceeds single file size limit "
                        f"({info.file_size / (1024*1024):.1f}MB > {MAX_SINGLE_FILE_BYTES / (1024*1024)}MB)."
                    )

                total_uncompressed_size += info.file_size
                if total_uncompressed_size > MAX_TOTAL_UNCOMPRESSED_BYTES:
                    raise ZipExtractionError(
                        f"Total uncompressed content exceeds safety limit "
                        f"({MAX_TOTAL_UNCOMPRESSED_BYTES / (1024*1024)}MB limit)."
                    )

                # Security Check: Path Traversal
                target_file_path = dest_path / info.filename
                if not is_safe_path(dest_path, target_file_path):
                    raise ZipExtractionError(
                        f"Malicious path traversal detected in archive entry: {info.filename}"
                    )

            # Extraction pass
            for info in infolist:
                if should_skip_member(info.filename):
                    skipped_count += 1
                    continue

                # Don't create special device files or symlinks
                if info.is_dir():
                    dir_path = dest_path / info.filename
                    dir_path.mkdir(parents=True, exist_ok=True)
                    continue

                target_file_path = dest_path / info.filename
                target_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Extract file contents safely
                with zf.open(info) as src, open(target_file_path, 'wb') as dst:
                    while chunk := src.read(65536):
                        dst.write(chunk)

                file_count += 1
                extracted_files.append(str(target_file_path))

    except zipfile.BadZipFile as e:
        raise ZipExtractionError(f"Corrupted or invalid ZIP file: {str(e)}")
    except Exception as e:
        if isinstance(e, ZipExtractionError):
            raise
        raise ZipExtractionError(f"Error while extracting archive: {str(e)}")

    # Detect if all files are inside a single root directory inside zip
    root_folder = str(dest_path)
    sub_entries = [p for p in dest_path.iterdir() if p.name not in IGNORED_DIRECTORY_NAMES]
    if len(sub_entries) == 1 and sub_entries[0].is_dir():
        # Cleanly use the inner root folder for more natural relative paths
        root_folder = str(sub_entries[0])

    return {
        'extracted_path': root_folder,
        'base_extracted_path': str(dest_path),
        'file_count': file_count,
        'total_size': total_uncompressed_size,
        'skipped_count': skipped_count,
        'extracted_files': extracted_files,
    }
