#!/usr/bin/env python3
"""DLT Log Reader - Parse and filter DLT log files.

This script reads DLT log files from data/dlt/ directory, filters messages
by CTID=CMSV, sorts them by timestamp, and saves the output to a text file.
"""

import os
from pathlib import Path
from dlt.dlt import cDLTFile


def read_dlt_files(dlt_dir, ctid_filter="CMSV"):
    """Read all DLT files and filter by CTID.
    
    Args:
        dlt_dir: Directory containing DLT files
        ctid_filter: Context ID to filter (default: "CMSV")
        
    Returns:
        List of tuples (timestamp, message_string)
    """
    dlt_files = list(Path(dlt_dir).glob("*.dlt"))
    
    if not dlt_files:
        print(f"No DLT files found in {dlt_dir}")
        return []
    
    print(f"Found {len(dlt_files)} DLT file(s)")
    
    all_messages = []
    
    for dlt_file_path in dlt_files:
        print(f"Processing: {dlt_file_path}")
        
        # Create DLT file reader with filter
        dlt_file = cDLTFile()
        filters = [("", ctid_filter)]  # Empty APID means any APID
        
        success = dlt_file.read(str(dlt_file_path), filters=filters)
        
        if not success:
            print(f"  Failed to read file: {dlt_file_path}")
            continue
        
        print(f"  Total messages: {dlt_file.counter_total}")
        print(f"  Filtered messages (CTID={ctid_filter}): {dlt_file.counter}")
        
        # Extract messages
        for msg in dlt_file:
            timestamp = msg.storage_timestamp
            if timestamp is None:
                # Skip messages with invalid timestamps
                continue
            message_str = str(msg)  # Use DLT's string representation
            all_messages.append((timestamp, message_str))
    
    return all_messages


def save_to_file(messages, output_file):
    """Save sorted messages to a text file.
    
    Args:
        messages: List of tuples (timestamp, message_string)
        output_file: Output file path
    """
    # Sort by timestamp
    sorted_messages = sorted(messages, key=lambda x: x[0])
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        for timestamp, message in sorted_messages:
            f.write(message + '\n')
    
    print(f"Saved {len(sorted_messages)} messages to: {output_file}")


def main():
    """Main function to parse DLT logs and save filtered output."""
    # Set up paths
    script_dir = Path(__file__).parent
    dlt_dir = script_dir / "data" / "dlt"
    output_dir = script_dir / "data" / "output"
    output_file = output_dir / "filtered_logs_CMSV.txt"
    
    print("DLT Log Reader")
    print("=" * 60)
    print(f"Input directory: {dlt_dir}")
    print(f"Output file: {output_file}")
    print(f"Filter: CTID=CMSV")
    print("=" * 60)
    
    # Read and filter DLT files
    messages = read_dlt_files(str(dlt_dir), ctid_filter="CMSV")
    
    if not messages:
        print("No messages found matching the filter criteria.")
        return
    
    # Save to output file
    save_to_file(messages, str(output_file))
    
    print("=" * 60)
    print("Processing complete!")


if __name__ == "__main__":
    main()
