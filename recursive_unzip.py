#!/usr/bin/env python3
"""
Recursive archive extraction script
Extracts all archives in a file or directory recursively until no archives remain
"""

import os
import sys
import zipfile
import tarfile
import gzip
import shutil
import argparse
from pathlib import Path


# Supported archive extensions
ARCHIVE_EXTENSIONS = {
    '.zip': 'zip',
    '.tar': 'tar',
    '.gz': 'tar',
    '.tgz': 'tar',
    '.bz2': 'tar',
    '.tbz': 'tar',
    '.tbz2': 'tar',
    '.xz': 'tar',
    '.txz': 'tar',
}


def detect_archive_type(file_path):
    """
    Detect the actual archive type by reading file magic bytes
    Returns: 'zip', 'tar', 'gzip', or None
    """
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(8)

        # Check for ZIP (PK\x03\x04 or PK\x05\x06 or PK\x07\x08)
        if magic[:2] == b'PK':
            return 'zip'

        # Check for gzip (0x1f 0x8b)
        if magic[:2] == b'\x1f\x8b':
            return 'gzip'

        # Check for tar (ustar at offset 257)
        with open(file_path, 'rb') as f:
            f.seek(257)
            tar_magic = f.read(5)
            if tar_magic == b'ustar':
                return 'tar'

        # Try to open as tarfile (handles compressed tar files)
        if tarfile.is_tarfile(file_path):
            return 'tar'

    except Exception:
        pass

    return None


def is_archive(file_path):
    """Check if a file is an archive based on extension or actual content"""
    file_path = Path(file_path)

    if not file_path.is_file():
        return False

    # Check for compound extensions like .tar.gz
    if file_path.suffix.lower() in ['.gz', '.bz2', '.xz']:
        stem = file_path.stem
        if stem.endswith('.tar'):
            return True

    # Check by extension
    if file_path.suffix.lower() in ARCHIVE_EXTENSIONS:
        return True

    # Check by actual file content for files with misleading extensions
    archive_type = detect_archive_type(file_path)
    return archive_type is not None


def extract_archive(archive_path, extract_to=None):
    """
    Extract an archive file
    Returns the extraction directory path or None if extraction failed
    """
    archive_path = Path(archive_path)

    if not archive_path.exists():
        print(f"Error: File not found: {archive_path}")
        return None

    # Detect actual archive type
    archive_type = detect_archive_type(archive_path)

    if archive_type is None:
        print(f"Cannot detect archive type: {archive_path}")
        return None

    # Create extraction directory (same name as archive without extension)
    if extract_to is None:
        if archive_path.suffix.lower() in ['.gz', '.bz2', '.xz'] and archive_path.stem.endswith('.tar'):
            # For .tar.gz, .tar.bz2, etc., remove both extensions
            extract_dir = archive_path.parent / archive_path.stem.replace('.tar', '')
        else:
            extract_dir = archive_path.parent / archive_path.stem
    else:
        extract_dir = Path(extract_to)

    # Create unique directory if it already exists
    original_extract_dir = extract_dir
    counter = 1
    while extract_dir.exists():
        extract_dir = Path(f"{original_extract_dir}_{counter}")
        counter += 1

    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting: {archive_path} (detected as {archive_type}) -> {extract_dir}")

    try:
        # Handle zip files
        if archive_type == 'zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

        # Handle tar files (including .tar.gz, .tar.bz2, .tar.xz)
        elif archive_type == 'tar':
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_dir)

        # Handle pure gzip files (not tar.gz)
        elif archive_type == 'gzip':
            # For pure gzip files, extract to a single file
            output_file = extract_dir / archive_path.stem
            with gzip.open(archive_path, 'rb') as gz_ref:
                with open(output_file, 'wb') as out_file:
                    shutil.copyfileobj(gz_ref, out_file)

        else:
            print(f"Unsupported archive format: {archive_path}")
            extract_dir.rmdir()
            return None

        print(f"Successfully extracted: {archive_path}")
        return extract_dir

    except Exception as e:
        print(f"Error extracting {archive_path}: {e}")
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        return None


def find_archives(directory):
    """Find all archive files in a directory"""
    archives = []
    directory = Path(directory)

    for item in directory.iterdir():
        if item.is_file() and is_archive(item):
            archives.append(item)
        elif item.is_dir():
            # Recursively search subdirectories
            archives.extend(find_archives(item))

    return archives


def flatten_directory(root_dir):
    """
    Move all files from nested directories to the root level
    Remove empty nested directories after moving files
    """
    root_dir = Path(root_dir)

    if not root_dir.is_dir():
        print(f"Error: {root_dir} is not a directory")
        return

    print(f"\nFlattening directory structure of: {root_dir}")

    # Collect all files recursively
    all_files = []
    for file_path in root_dir.rglob('*'):
        if file_path.is_file():
            all_files.append(file_path)

    print(f"Found {len(all_files)} files to move to top level")

    # Move all files to root directory
    moved_count = 0
    for file_path in all_files:
        # Skip if already at root level
        if file_path.parent == root_dir:
            continue

        # Create unique filename if collision
        target_path = root_dir / file_path.name
        original_target = target_path
        counter = 1
        while target_path.exists():
            stem = original_target.stem
            suffix = original_target.suffix
            target_path = root_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        # Move file
        try:
            shutil.move(str(file_path), str(target_path))
            moved_count += 1
        except Exception as e:
            print(f"Warning: Could not move {file_path}: {e}")

    print(f"Moved {moved_count} files to root level")

    # Remove empty directories
    removed_dirs = 0
    for dir_path in sorted(root_dir.rglob('*'), key=lambda p: len(str(p)), reverse=True):
        if dir_path.is_dir() and dir_path != root_dir:
            try:
                dir_path.rmdir()
                removed_dirs += 1
            except OSError:
                # Directory not empty, skip
                pass

    print(f"Removed {removed_dirs} empty directories")
    print(f"Flattening complete!")


def recursive_extract(path, max_depth=10):
    """
    Recursively extract all archives in a file or directory

    Args:
        path: File or directory path to process
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Path to the final extraction directory, or None
    """
    path = Path(path).resolve()

    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        return None

    depth = 0
    initial_was_file = path.is_file()
    extracted_dir_from_initial = None

    while depth < max_depth:
        print(f"\n--- Extraction pass {depth + 1} ---")

        # Find all archives
        # If the initial path was a file and has been extracted/deleted,
        # switch to the extracted directory
        if initial_was_file and extracted_dir_from_initial and not path.exists():
            path = extracted_dir_from_initial
            initial_was_file = False  # Now treat it as a directory

        if path.is_file():
            if is_archive(path):
                archives = [path]
            else:
                print(f"File {path} is not an archive")
                return
        elif path.is_dir():
            archives = find_archives(path)
        else:
            print(f"Path no longer exists: {path}")
            break

        if not archives:
            print("No more archives found. Extraction complete!")
            break

        print(f"Found {len(archives)} archive(s) to extract")

        # Extract all archives
        extracted_any = False
        for archive in archives:
            if archive.exists():  # Check if still exists (might have been deleted)
                extract_dir = extract_archive(archive)
                if extract_dir:
                    extracted_any = True
                    # Remember the first extracted directory if we started with a file
                    if depth == 0 and initial_was_file and extracted_dir_from_initial is None:
                        extracted_dir_from_initial = extract_dir
                    # Delete the original archive after successful extraction
                    try:
                        archive.unlink()
                        print(f"Deleted original archive: {archive}")
                    except Exception as e:
                        print(f"Warning: Could not delete {archive}: {e}")

        if not extracted_any:
            print("No archives were successfully extracted")
            break

        depth += 1

    if depth >= max_depth:
        print(f"\nWarning: Reached maximum recursion depth ({max_depth})")
        print("There may still be archives remaining")

    # Return the extraction directory for potential flattening
    if initial_was_file and extracted_dir_from_initial:
        return extracted_dir_from_initial
    elif path.is_dir():
        return path
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Recursively extract all archives in a file or directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported formats:
  - ZIP (.zip)
  - TAR (.tar)
  - GZIP (.tar.gz, .tgz)
  - BZIP2 (.tar.bz2, .tbz, .tbz2)
  - XZ (.tar.xz, .txz)

Example usage:
  %(prog)s my_archive.zip
  %(prog)s /path/to/directory
  %(prog)s archive.tar.gz --max-depth 5
        """
    )

    parser.add_argument(
        'path',
        help='File or directory path to extract'
    )

    parser.add_argument(
        '--max-depth',
        type=int,
        default=10,
        help='Maximum recursion depth (default: 10)'
    )

    parser.add_argument(
        '--flatten',
        action='store_true',
        help='Move all extracted files to the top level directory, removing nested structure'
    )

    args = parser.parse_args()

    print(f"Starting recursive extraction of: {args.path}")
    print(f"Maximum recursion depth: {args.max_depth}\n")

    extraction_dir = recursive_extract(args.path, args.max_depth)

    print("\n=== Extraction process finished ===")

    # Flatten directory structure if requested
    if args.flatten and extraction_dir and extraction_dir.exists():
        flatten_directory(extraction_dir)


if __name__ == '__main__':
    main()
