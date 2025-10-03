#!/usr/bin/env python3
"""Extract H.264 videos from ROS bags using exposure_time for accurate framerate."""

import os
import sys
import subprocess


def extract_h264_from_bag(bag_path, output_dir=None):
    """
    Extract H.264 data from bag file and generate MP4 with correct framerate.

    Args:
        bag_path: Path to bag file
        output_dir: Output directory (defaults to bag directory)

    Returns:
        dict: Camera names to H.264 file paths
    """
    if not os.path.exists(bag_path):
        print(f"Error: bag file not found: {bag_path}")
        return {}

    if output_dir is None:
        bag_abs_path = os.path.abspath(bag_path)
        output_dir = os.path.dirname(bag_abs_path)
        if not output_dir:
            output_dir = '.'
    else:
        os.makedirs(output_dir, exist_ok=True)

    print(f"Reading bag: {bag_path}")

    # Inject fake roslz4 module for LZ4 support
    try:
        import lz4.frame

        class FakeRosLZ4:
            @staticmethod
            def decompress(data):
                return lz4.frame.decompress(data)

        import sys
        sys.modules['roslz4'] = FakeRosLZ4()
        import rosbag

        print(f"LZ4 support enabled (found_lz4={rosbag.bag.found_lz4})")

    except ImportError as e:
        print(f"Error: {e}")
        print("Install: pip install bagpy lz4")
        return {}

    try:
        bag = rosbag.Bag(bag_path, 'r', chunk_threshold=256*1024*1024, allow_unindexed=True)
    except Exception as e:
        print(f"Error opening bag: {e}")
        import traceback
        traceback.print_exc()
        return {}

    try:
        info = bag.get_type_and_topic_info()
        all_topics = info[1].keys()
        print(f"\nFound {len(all_topics)} topics")
    except Exception as e:
        print(f"Error reading topics: {e}")
        bag.close()
        return {}

    # Find camera topics matching /C/Camera/*
    camera_topics = {}
    for topic in all_topics:
        if topic.startswith('/C/Camera/'):
            camera_name = topic.split('/')[-1]
            camera_topics[topic] = camera_name

    if not camera_topics:
        print("Warning: No /C/Camera/* topics found")
        bag.close()
        return {}

    print(f"\nFound {len(camera_topics)} camera topics:")
    for topic, camera_name in camera_topics.items():
        print(f"  - {topic} -> {camera_name}")

    output_files = {}
    file_handles = {}
    message_counts = {}
    timestamps = {}

    for topic, camera_name in camera_topics.items():
        output_file = os.path.join(output_dir, f"{camera_name}.h264")
        output_files[camera_name] = output_file
        file_handles[topic] = open(output_file, 'wb')
        message_counts[camera_name] = 0
        timestamps[camera_name] = []
        print(f"Output: {output_file}")

    print("\nExtracting H.264 data...")

    try:
        for topic, msg, _ in bag.read_messages(topics=list(camera_topics.keys())):
            camera_name = camera_topics[topic]

            data = None
            if hasattr(msg, 'imageData'):
                data = bytes(msg.imageData)
            elif hasattr(msg, 'data'):
                data = bytes(msg.data)
            elif hasattr(msg, 'image') and hasattr(msg.image, 'data'):
                data = bytes(msg.image.data)

            if data and len(data) > 0:
                file_handles[topic].write(data)
                message_counts[camera_name] += 1

                if hasattr(msg, 'exposure_time_s') and hasattr(msg, 'exposure_time_ns'):
                    timestamp = msg.exposure_time_s + msg.exposure_time_ns / 1e9
                    timestamps[camera_name].append(timestamp)

                if message_counts[camera_name] % 100 == 0:
                    print(f"  {camera_name}: {message_counts[camera_name]} frames", end='\r')

    except Exception as e:
        print(f"\nError reading messages: {e}")
        import traceback
        traceback.print_exc()
    finally:
        for fh in file_handles.values():
            fh.close()
        bag.close()

    print("\n\nExtraction complete:")
    for camera_name in camera_topics.values():
        if camera_name in output_files:
            output_file = output_files[camera_name]
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                count = message_counts.get(camera_name, 0)
                print(f"  - {camera_name}: {count} frames, {file_size / 1024 / 1024:.2f} MB")

    # Generate MP4 with correct framerate from exposure_time
    print("\nGenerating MP4 files with correct framerate...")
    for camera_name in camera_topics.values():
        if camera_name in output_files and timestamps.get(camera_name):
            h264_file = output_files[camera_name]
            mp4_file = h264_file.replace('.h264', '.mp4')

            ts_list = timestamps[camera_name]
            if len(ts_list) > 1:
                time_diffs = [ts_list[i+1] - ts_list[i] for i in range(len(ts_list)-1)]
                avg_interval = sum(time_diffs) / len(time_diffs)
                actual_fps = 1.0 / avg_interval if avg_interval > 0 else 20.0

                print(f"\n  {camera_name}:")
                print(f"    FPS: {actual_fps:.2f} Hz")
                print(f"    Avg interval: {avg_interval*1000:.2f} ms")

                try:
                    cmd = [
                        'ffmpeg', '-y',
                        '-r', str(actual_fps),
                        '-i', h264_file,
                        '-c:v', 'copy',
                        '-r', str(actual_fps),
                        mp4_file
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"    ✓ MP4: {mp4_file}")
                    else:
                        print(f"    ✗ ffmpeg failed: {result.stderr[:200]}")
                except Exception as e:
                    print(f"    ✗ Error: {e}")

    return output_files


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print("Usage: python bag_helper.py <bag_file_path> [output_directory]")
        print("\nExamples:")
        print("  python bag_helper.py data.bag")
        print("  python bag_helper.py data.bag ./output")
        sys.exit(1)

    bag_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    output_files = extract_h264_from_bag(bag_path, output_dir)

    if output_files:
        print("\nSuccess:")
        for camera_name, file_path in output_files.items():
            print(f"  {camera_name}: {file_path}")
    else:
        print("\nFailed to extract H.264 files")
        sys.exit(1)


if __name__ == "__main__":
    main()
