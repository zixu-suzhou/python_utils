#!/usr/bin/env python3
"""
ASW Downloader - Entry point script

This script provides backward compatibility with the old interface
while using the new modular implementation.

Usage: python asw_downloader.py <filename> [options]
"""

from asw_downloader.cli import main

if __name__ == "__main__":
    main()
