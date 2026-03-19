#!/usr/bin/env python3
"""Compare and sync <project name=.. revision=..> between snapshot_ref.txt and int/int.xml.

Usage:
  python3 scripts/sync_revisions.py --tag <git_tag> --int int/int.xml [--apply]
  python3 scripts/sync_revisions.py --snapshot snapshot_ref.txt --int int/int.xml [--apply]

By default the script performs a dry-run and prints the changes. Use `--apply` to
backup and write the updated `int.xml`.
"""
import argparse
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import re


def parse_snapshot(snapshot_path):
    tree = ET.parse(snapshot_path)
    root = tree.getroot()
    projects = {}
    for p in root.findall('project'):
        name = p.get('name')
        rev = p.get('revision')
        if name and rev:
            projects[name] = rev
    return projects


def parse_snapshot_from_tag(tag):
    """Read snapshot/static_snapshot.xml from the given git tag and return projects map."""
    git_path = f'{tag}:snapshot/static_snapshot.xml'
    try:
        result = subprocess.run(
            ['git', 'show', git_path],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        print(f'Error: cannot read {git_path!r} from git: {e.stderr.strip()}', file=sys.stderr)
        sys.exit(2)
    root = ET.fromstring(result.stdout)
    projects = {}
    for p in root.findall('project'):
        name = p.get('name')
        rev = p.get('revision')
        if name and rev:
            projects[name] = rev
    return projects


def sync_int(int_path, snapshot_map, apply=False):
    """Textual-only replacement of `revision` attributes for matching project `name`.

    This preserves original formatting and only updates/insert the `revision` attribute
    inside the matching `<project ...>` start tag.
    """
    p = Path(int_path)
    text = p.read_text(encoding='utf-8')
    changes = []

    for name, want_rev in snapshot_map.items():
        # find the first project tag with this name
        pattern = re.compile(r'(<project\b[^>]*\bname\s*=\s*"%s"[^>]*)(>)' % re.escape(name), re.DOTALL)

        def repl(m, want_rev=want_rev, name=name):
            attrs = m.group(1)
            # look for existing revision attribute
            mrev = re.search(r'\brevision\s*=\s*"([^"]*)"', attrs)
            old = mrev.group(1) if mrev else None
            if old == want_rev:
                return m.group(0)
            # record change
            changes.append((name, old, want_rev))
            if mrev:
                # replace existing revision value
                def rep(mm):
                    return mm.group(1) + want_rev + mm.group(3)
                new_attrs = re.sub(r'(\brevision\s*=\s*")([^\"]*)(\")', rep, attrs, count=1)
            else:
                # insert revision before closing slash (self-closing tags end with /)
                stripped = attrs.rstrip()
                if stripped.endswith('/'):
                    new_attrs = stripped[:-1].rstrip() + ' revision="' + want_rev + '"/'
                else:
                    new_attrs = attrs + ' revision="' + want_rev + '"'
            return new_attrs + m.group(2)

        text, n = pattern.subn(repl, text, count=1)

    if not changes:
        print('No changes needed.')
        return 0

    print('Detected changes:')
    for name, old, new in changes:
        print(f'- {name}: {old!r} -> {new!r}')

    if apply:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak = p.with_name(p.name + f'.bak.{ts}')
        shutil.copy2(p, bak)
        p.write_text(text, encoding='utf-8')
        print(f'Applied changes and backed up original to {bak}')
    else:
        print('\nDry-run: no file written. Re-run with --apply to perform updates.')

    return 0


def main():
    parser = argparse.ArgumentParser(description='Sync revisions from snapshot to int.xml')
    src = parser.add_mutually_exclusive_group()
    src.add_argument('--tag', help='git tag to read snapshot/static_snapshot.xml from')
    src.add_argument('--snapshot', default='snapshot_ref.txt', help='path to snapshot_ref.txt (default: snapshot_ref.txt)')
    parser.add_argument('--int', dest='intxml', default='int/int.xml', help='path to int.xml')
    parser.add_argument('--apply', action='store_true', help='apply updates to int.xml (default: dry-run)')
    args = parser.parse_args()

    intr = Path(args.intxml)
    if not intr.exists():
        print(f'Error: int.xml file not found: {intr}', file=sys.stderr)
        return 2

    if args.tag:
        print(f'Reading snapshot from git tag: {args.tag}')
        snapshot_map = parse_snapshot_from_tag(args.tag)
    else:
        snap = Path(args.snapshot)
        if not snap.exists():
            print(f'Error: snapshot file not found: {snap}', file=sys.stderr)
            return 2
        snapshot_map = parse_snapshot(snap)

    return sync_int(intr, snapshot_map, apply=args.apply)


if __name__ == '__main__':
    sys.exit(main())
