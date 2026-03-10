#!/usr/bin/env python3
"""Analyze frame alignment across cameras based on exposure timestamps."""

import os
import sys
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np


def load_exposure_data(csv_file):
    """
    Load exposure timestamp data from CSV file.

    Args:
        csv_file: Path to CSV file with frame_id,exposure_timestamp_s

    Returns:
        list: List of dicts with 'frame_id' and 'timestamp'
    """
    data = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'frame_id': int(row['frame_id']),
                'timestamp': float(row['exposure_timestamp_s'])
            })
    return data


def find_aligned_frames(camera_data, base_camera='FrontWide', max_diff_ms=10.0):
    """
    Find aligned frames across all cameras.

    Args:
        camera_data: Dict of camera_name -> list of frame data
        base_camera: Base camera to align against
        max_diff_ms: Maximum timestamp difference in milliseconds

    Returns:
        tuple: (first_aligned_timestamp, aligned_frames_list)
    """
    if base_camera not in camera_data:
        print(f"Error: Base camera '{base_camera}' not found")
        return None, []

    base_frames = camera_data[base_camera]
    other_cameras = {name: data for name, data in camera_data.items() if name != base_camera}

    if not other_cameras:
        print(f"Error: No other cameras found besides {base_camera}")
        return None, []

    max_diff_s = max_diff_ms / 1000.0
    aligned_frames = []
    first_aligned_ts = None

    # For each camera, maintain an index pointer
    camera_indices = {name: 0 for name in other_cameras.keys()}

    for base_idx, base_frame in enumerate(base_frames):
        base_ts = base_frame['timestamp']

        # Try to find matching frames in all other cameras
        matched = {}
        all_matched = True

        for cam_name, cam_frames in other_cameras.items():
            # Start from current index
            idx = camera_indices[cam_name]
            best_match = None
            best_diff = float('inf')
            best_idx = idx

            # Search forward for best match within threshold
            while idx < len(cam_frames):
                cam_ts = cam_frames[idx]['timestamp']
                diff = abs(cam_ts - base_ts)

                if diff <= max_diff_s:
                    if diff < best_diff:
                        best_diff = diff
                        best_idx = idx
                        best_match = {
                            'frame_id': cam_frames[idx]['frame_id'],
                            'timestamp': cam_ts,
                            'diff_ms': diff * 1000.0
                        }
                    idx += 1
                elif cam_ts > base_ts + max_diff_s:
                    # Gone too far
                    break
                else:
                    idx += 1

            if best_match:
                matched[cam_name] = best_match
                # Update index to the matched position (don't skip ahead too much)
                camera_indices[cam_name] = best_idx
            else:
                all_matched = False
                break

        if all_matched and len(matched) == len(other_cameras):
            # Found aligned frame set
            aligned_set = {
                base_camera: {
                    'frame_id': base_frame['frame_id'],
                    'timestamp': base_ts,
                    'diff_ms': 0.0
                }
            }
            aligned_set.update(matched)
            aligned_frames.append(aligned_set)

            if first_aligned_ts is None:
                first_aligned_ts = base_ts

    return first_aligned_ts, aligned_frames


def plot_timestamps(camera_data, aligned_frames, base_camera, output_file='timestamps_plot.png', show_plot=True):
    """
    Plot all camera timestamps on a single figure.

    Args:
        camera_data: Dict of camera_name -> list of frame data
        aligned_frames: List of aligned frame sets
        base_camera: Base camera name
        output_file: Output image file path
        show_plot: Whether to show interactive plot window
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Get all camera names sorted
    camera_names = sorted(camera_data.keys())
    colors = plt.cm.tab10(np.linspace(0, 1, len(camera_names)))

    # Find global time range
    all_timestamps = []
    for data in camera_data.values():
        all_timestamps.extend([frame['timestamp'] for frame in data])

    if not all_timestamps:
        print("Warning: No timestamps to plot")
        return

    min_ts = min(all_timestamps)
    max_ts = max(all_timestamps)

    # Plot 1: All timestamps (relative to first timestamp)
    for idx, camera_name in enumerate(camera_names):
        frames = camera_data[camera_name]
        timestamps = [frame['timestamp'] - min_ts for frame in frames]
        frame_indices = list(range(len(frames)))

        ax1.scatter(timestamps, [idx] * len(timestamps),
                   c=[colors[idx]], label=camera_name, s=10, alpha=0.6)

    ax1.set_xlabel('Time (s)', fontsize=12)
    ax1.set_ylabel('Camera', fontsize=12)
    ax1.set_yticks(range(len(camera_names)))
    ax1.set_yticklabels(camera_names)
    ax1.set_title('Camera Exposure Timestamps (All Frames)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', fontsize=8)

    # Plot 2: Aligned frames only
    if aligned_frames:
        for idx, camera_name in enumerate(camera_names):
            aligned_ts = []
            for frame_set in aligned_frames:
                if camera_name in frame_set:
                    aligned_ts.append(frame_set[camera_name]['timestamp'] - min_ts)

            if aligned_ts:
                ax2.scatter(aligned_ts, [idx] * len(aligned_ts),
                           c=[colors[idx]], label=camera_name, s=20, alpha=0.8, marker='o')

        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Camera', fontsize=12)
        ax2.set_yticks(range(len(camera_names)))
        ax2.set_yticklabels(camera_names)
        ax2.set_title(f'Aligned Frames Only (base: {base_camera}, total: {len(aligned_frames)})',
                     fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")

    if show_plot:
        plt.show()
    else:
        plt.close()


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_frame_alignment.py <data_directory> [base_camera] [max_diff_ms]")
        print("\nExamples:")
        print("  python analyze_frame_alignment.py ./data")
        print("  python analyze_frame_alignment.py ./data FrontWide 10.0")
        sys.exit(1)

    data_dir = sys.argv[1]
    base_camera = sys.argv[2] if len(sys.argv) > 2 else 'FrontWide'
    max_diff_ms = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0

    if not os.path.exists(data_dir):
        print(f"Error: Directory not found: {data_dir}")
        sys.exit(1)

    # Find all exposure time CSV files
    csv_files = {}
    for filename in os.listdir(data_dir):
        if filename.endswith('_exposure_time.csv'):
            camera_name = filename.replace('_exposure_time.csv', '')
            csv_path = os.path.join(data_dir, filename)
            csv_files[camera_name] = csv_path

    if not csv_files:
        print(f"Error: No *_exposure_time.csv files found in {data_dir}")
        sys.exit(1)

    print(f"Found {len(csv_files)} cameras:")
    for camera_name in sorted(csv_files.keys()):
        print(f"  - {camera_name}")

    # Load exposure data for all cameras
    print(f"\nLoading exposure timestamp data...")
    camera_data = {}
    for camera_name, csv_path in csv_files.items():
        data = load_exposure_data(csv_path)
        camera_data[camera_name] = data
        print(f"  {camera_name}: {len(data)} frames")

    # Find aligned frames
    print(f"\nFinding aligned frames...")
    print(f"  Base camera: {base_camera}")
    print(f"  Max timestamp diff: {max_diff_ms} ms")

    first_aligned_ts, aligned_frames = find_aligned_frames(
        camera_data,
        base_camera=base_camera,
        max_diff_ms=max_diff_ms
    )

    # Generate plot first (always do this)
    output_plot = os.path.join(data_dir, 'timestamps_plot.png')
    plot_timestamps(camera_data, aligned_frames, base_camera, output_plot)

    if first_aligned_ts is None:
        print(f"\nWarning: Could not find aligned frames")
        print(f"Check the plot to analyze alignment issues: {output_plot}")
        return

    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"\nFirst aligned timestamp: {first_aligned_ts:.9f} s")
    print(f"Total aligned frames: {len(aligned_frames)}")

    if aligned_frames:
        print(f"\nFirst aligned frame set:")
        first_set = aligned_frames[0]
        for camera_name in sorted(first_set.keys()):
            frame_info = first_set[camera_name]
            print(f"  {camera_name:20s} frame_id={frame_info['frame_id']:6d}  "
                  f"ts={frame_info['timestamp']:.9f}  diff={frame_info['diff_ms']:6.3f} ms")

        # Show some statistics
        print(f"\nAlignment statistics:")
        max_diffs_per_camera = defaultdict(list)
        for frame_set in aligned_frames:
            for camera_name, frame_info in frame_set.items():
                if camera_name != base_camera:
                    max_diffs_per_camera[camera_name].append(frame_info['diff_ms'])

        for camera_name in sorted(max_diffs_per_camera.keys()):
            diffs = max_diffs_per_camera[camera_name]
            avg_diff = sum(diffs) / len(diffs)
            max_diff = max(diffs)
            print(f"  {camera_name:20s} avg_diff={avg_diff:6.3f} ms  max_diff={max_diff:6.3f} ms")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
