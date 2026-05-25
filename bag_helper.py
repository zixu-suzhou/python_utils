#!/usr/bin/env python3
"""Extract H.264/YUV videos/images from ROS bags using exposure_time for accurate framerate."""

import os
import sys
import subprocess
import argparse
import io
import time


# Constants for optimization
BATCH_WRITE_SIZE = 50  # Write to disk every N frames for better performance
DEFAULT_BUFFER_SIZE = 10 * 1024 * 1024  # 10MB write buffer


def sample_frames_by_hz(timestamps, sample_hz):
    """
    Select frame indices to sample based on desired Hz.

    Args:
        timestamps: List of frame timestamps in seconds
        sample_hz: Desired sampling rate in Hz (frames per second)

    Returns:
        list: Indices of frames to keep
    """
    if not timestamps or sample_hz <= 0:
        return []

    if len(timestamps) == 1:
        return [0]

    sampled_indices = []
    interval = 1.0 / sample_hz  # Time interval between samples

    # Always include first frame
    sampled_indices.append(0)
    last_sampled_time = timestamps[0]

    for idx, ts in enumerate(timestamps[1:], start=1):
        if ts - last_sampled_time >= interval:
            sampled_indices.append(idx)
            last_sampled_time = ts

    return sampled_indices


def extract_h264_from_bag(bag_path, output_dir=None, camera_names=None, output_format='h264', sample_hz=1.0, buffer_size=DEFAULT_BUFFER_SIZE):
    """
    Extract H.264/YUV data from bag file and generate outputs with correct framerate.

    Args:
        bag_path: Path to bag file
        output_dir: Output directory (defaults to bag directory)
        camera_names: List of camera names to process (None = process all)
        output_format: Output format - 'h264', 'mp4', or 'yuv'
        sample_hz: Sampling rate in Hz for YUV output (frames per second)
        buffer_size: Write buffer size in bytes (default: 10MB for better I/O performance)

    Returns:
        dict: Camera names to output file paths
    """
    if not os.path.exists(bag_path):
        print(f"Error: bag file not found: {bag_path}")
        return {}

    if output_dir is None:
        bag_abs_path = os.path.abspath(bag_path)
        output_dir = os.path.dirname(bag_abs_path)
        if not output_dir:
            output_dir = "."
    else:
        os.makedirs(output_dir, exist_ok=True)

    print(f"Reading bag: {bag_path}")
    start_time = time.time()

    # Inject fake roslz4 module for LZ4 support
    try:
        import lz4.frame

        class FakeRosLZ4:
            @staticmethod
            def decompress(data):
                return lz4.frame.decompress(data)

        import sys

        sys.modules["roslz4"] = FakeRosLZ4()

        # Monkey-patch genpy.dynamic for Windows compatibility
        import genpy.dynamic
        import tempfile
        import re

        _original_generate = genpy.dynamic.generate_dynamic

        def _patched_generate_dynamic(msg_cat, msg_def):
            """Windows-compatible version of generate_dynamic with encoding fix."""
            # Clean msg_def to remove problematic characters
            # The issue is that byte 0xa0 (non-breaking space) is not valid UTF-8
            if isinstance(msg_def, bytes):
                # Replace byte 0xa0 and other problematic bytes
                msg_def = msg_def.replace(
                    b"\xa0", b" "
                )  # non-breaking space -> regular space
                msg_def = (
                    msg_def.decode("latin1", errors="replace")
                    .encode("utf-8", errors="replace")
                    .decode("utf-8")
                )
            elif isinstance(msg_def, str):
                # Clean the string
                msg_def = msg_def.replace(
                    "\xa0", " "
                )  # non-breaking space -> regular space
                # Ensure it's clean UTF-8
                msg_def = msg_def.encode("utf-8", errors="replace").decode("utf-8")

            try:
                result = _original_generate(msg_cat, msg_def)
            except (FileNotFoundError, OSError) as e:
                # Handle /tmp/foo issue on Windows
                if "/tmp/foo" in str(e):
                    import builtins

                    _orig_open = builtins.open

                    def _temp_open(f, *args, **kwargs):
                        if f == "/tmp/foo":
                            f = os.path.join(tempfile.gettempdir(), "genpy_debug.txt")
                        return _orig_open(f, *args, **kwargs)

                    builtins.open = _temp_open
                    try:
                        result = _original_generate(msg_cat, msg_def)
                    finally:
                        builtins.open = _orig_open
                else:
                    raise
            return result

        genpy.dynamic.generate_dynamic = _patched_generate_dynamic

        import rosbag

        print(f"LZ4 support enabled (found_lz4={rosbag.bag.found_lz4})")

    except ImportError as e:
        print(f"Error: {e}")
        print("Install: pip install bagpy lz4")
        return {}

    try:
        # Use larger chunk threshold for faster reading (512MB instead of 256MB)
        bag = rosbag.Bag(
            bag_path, "r", chunk_threshold=512 * 1024 * 1024, allow_unindexed=True
        )
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
        if topic.startswith("/C/Camera/"):
            camera_name = topic.split("/")[-1]
            # Filter by camera names if specified
            if camera_names is None or camera_name in camera_names:
                camera_topics[topic] = camera_name

    if not camera_topics:
        if camera_names:
            print(f"Warning: No matching cameras found for: {camera_names}")
        else:
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
    exposure_time_files = {}
    frame_data = {}
    temp_h264_files = {}  # For YUV conversion
    write_buffers = {}  # Write buffers for batched writes

    # For YUV/JPEG output, create subdirectories and temp H.264 files
    if output_format in ('yuv', 'jpeg'):
        for topic, camera_name in camera_topics.items():
            camera_output_dir = os.path.join(output_dir, camera_name)
            os.makedirs(camera_output_dir, exist_ok=True)
            output_files[camera_name] = camera_output_dir

            # Temporary H.264 file for decoding
            temp_h264 = os.path.join(output_dir, f"{camera_name}_temp.h264")
            temp_h264_files[camera_name] = temp_h264
            file_handles[topic] = open(temp_h264, "wb", buffering=buffer_size)

            message_counts[camera_name] = 0
            timestamps[camera_name] = []
            frame_data[camera_name] = []
            write_buffers[camera_name] = []  # Initialize write buffer
            print(f"Output directory: {camera_output_dir}")
    else:
        # For H.264/MP4 output
        for topic, camera_name in camera_topics.items():
            output_file = os.path.join(output_dir, f"{camera_name}.h264")
            exposure_time_file = os.path.join(
                output_dir, f"{camera_name}_exposure_time.csv"
            )
            output_files[camera_name] = output_file
            exposure_time_files[camera_name] = exposure_time_file
            file_handles[topic] = open(output_file, "wb", buffering=buffer_size)
            message_counts[camera_name] = 0
            timestamps[camera_name] = []
            frame_data[camera_name] = []
            write_buffers[camera_name] = []  # Initialize write buffer
            print(f"Output: {output_file}")
            print(f"Exposure time: {exposure_time_file}")

    if output_format in ('yuv', 'jpeg'):
        print(f"\nExtracting {output_format.upper()} images...")
    else:
        print("\nExtracting H.264 data...")

    try:
        for topic, msg, _ in bag.read_messages(topics=list(camera_topics.keys())):
            camera_name = camera_topics[topic]

            data = None
            if hasattr(msg, "imageData"):
                data = bytes(msg.imageData)
            elif hasattr(msg, "data"):
                data = bytes(msg.data)
            elif hasattr(msg, "image") and hasattr(msg.image, "data"):
                data = bytes(msg.image.data)

            if data and len(data) > 0:
                # Get exposure timestamp
                timestamp = None
                if hasattr(msg, "exposure_time_s") and hasattr(msg, "exposure_time_ns"):
                    timestamp = msg.exposure_time_s + msg.exposure_time_ns / 1e9
                    timestamps[camera_name].append(timestamp)

                    # Get frame_id from message
                    frame_id = msg.frame_id if hasattr(msg, "frame_id") else None

                    frame_data[camera_name].append(
                        {"frame_id": frame_id, "timestamp": timestamp}
                    )

                # Batch writes for better performance
                write_buffers[camera_name].append(data)
                message_counts[camera_name] += 1

                # Write to disk in batches
                if len(write_buffers[camera_name]) >= BATCH_WRITE_SIZE:
                    # Use b''.join() for efficient concatenation and single write
                    file_handles[topic].write(b''.join(write_buffers[camera_name]))
                    write_buffers[camera_name].clear()

                if message_counts[camera_name] % 100 == 0:
                    print(
                        f"  {camera_name}: {message_counts[camera_name]} frames",
                        end="\r",
                    )

        # Write remaining buffered data
        for camera_name in camera_topics.values():
            if camera_name in write_buffers and write_buffers[camera_name]:
                # Find the topic for this camera
                topic_for_camera = None
                for topic, cname in camera_topics.items():
                    if cname == camera_name:
                        topic_for_camera = topic
                        break
                if topic_for_camera and topic_for_camera in file_handles:
                    # Use b''.join() for efficient concatenation and single write
                    file_handles[topic_for_camera].write(b''.join(write_buffers[camera_name]))
                    write_buffers[camera_name].clear()

    except Exception as e:
        print(f"\nError reading messages: {e}")
        import traceback

        traceback.print_exc()
    finally:
        for fh in file_handles.values():
            fh.close()
        bag.close()

    # Save exposure times to CSV files (for H.264/MP4 output)
    if output_format not in ('yuv', 'jpeg'):
        print("\nSaving exposure times...")
        for camera_name in camera_topics.values():
            if camera_name in exposure_time_files and frame_data.get(camera_name):
                exposure_file = exposure_time_files[camera_name]
                with open(exposure_file, "w") as f:
                    f.write("frame_id,exposure_timestamp_s\n")
                    for data in frame_data[camera_name]:
                        frame_id = data["frame_id"] if data["frame_id"] is not None else ""
                        ts_s = data["timestamp"]
                        f.write(f"{frame_id},{ts_s:.9f}\n")
                print(
                    f"  - {camera_name}: {len(frame_data[camera_name])} frames saved to CSV"
                )

    # Convert H.264 to NV12 YUV images with frame sampling
    if output_format == 'yuv':
        print("\n\nConverting H.264 to NV12 YUV images...")
        for camera_name in camera_topics.values():
            if camera_name not in temp_h264_files:
                continue

            h264_file = temp_h264_files[camera_name]
            output_dir_camera = output_files[camera_name]

            if not os.path.exists(h264_file):
                print(f"  - {camera_name}: H.264 file not found")
                continue

            # Get timestamps for this camera
            ts_list = timestamps.get(camera_name, [])
            if not ts_list:
                print(f"  - {camera_name}: No timestamps found")
                continue

            # Sample frames based on desired Hz
            sampled_indices = sample_frames_by_hz(ts_list, sample_hz)

            print(f"\n  {camera_name}: Total frames: {len(ts_list)}")
            print(f"    Sampling at {sample_hz} Hz -> {len(sampled_indices)} frames selected")

            if not sampled_indices:
                print(f"    No frames to process")
                continue

            try:
                # Get video resolution from ffprobe
                probe_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=p=0",
                    h264_file
                ]

                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                if probe_result.returncode != 0:
                    print(f"    ✗ ffprobe failed: {probe_result.stderr[:200]}")
                    continue

                resolution = probe_result.stdout.strip().split(',')
                if len(resolution) != 2:
                    print(f"    ✗ Could not detect resolution")
                    continue

                width, height = int(resolution[0]), int(resolution[1])
                frame_size = width * height * 3 // 2  # NV12 format

                print(f"    Resolution: {width}x{height}")
                print(f"    Frame size: {frame_size} bytes ({frame_size / 1024 / 1024:.2f} MB per frame)")

                # Calculate FPS for proper decoding
                if len(ts_list) > 1:
                    time_diffs = [ts_list[i + 1] - ts_list[i] for i in range(len(ts_list) - 1)]
                    avg_interval = sum(time_diffs) / len(time_diffs)
                    actual_fps = 1.0 / avg_interval if avg_interval > 0 else 20.0
                else:
                    actual_fps = 20.0

                # Build frame selection expression for ffmpeg
                select_expr = '+'.join([f'eq(n,{idx})' for idx in sampled_indices])

                # Use ffmpeg to decode H.264 and stream NV12 YUV to stdout
                print(f"    Decoding H.264 to NV12 YUV with frame selection...")
                cmd = [
                    "ffmpeg",
                    "-v", "error",
                    "-r", str(actual_fps),
                    "-i", h264_file,
                    "-vf", f"select='{select_expr}'",
                    "-vsync", "0",
                    "-f", "rawvideo",
                    "-pix_fmt", "nv12",
                    "-"
                ]

                # Start ffmpeg process
                ffmpeg_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                # Read and save sampled frames with timestamp names
                frames_written = 0
                for idx in sampled_indices:
                    frame_data_bytes = ffmpeg_process.stdout.read(frame_size)

                    if len(frame_data_bytes) < frame_size:
                        print(f"    Warning: Frame {idx} incomplete ({len(frame_data_bytes)} bytes, expected {frame_size})")
                        break

                    timestamp = ts_list[idx]
                    timestamp_str = f"{timestamp:.9f}".replace('.', '_')
                    yuv_filename = f"{camera_name}_{timestamp_str}.yuv"
                    yuv_path = os.path.join(output_dir_camera, yuv_filename)

                    with open(yuv_path, 'wb') as yuv_f:
                        yuv_f.write(frame_data_bytes)

                    frames_written += 1

                    if frames_written % 10 == 0:
                        print(f"    Processed {frames_written}/{len(sampled_indices)} frames...", end='\r')

                # Wait for ffmpeg to complete
                ffmpeg_process.wait()

                print(f"    ✓ Converted {frames_written}/{len(sampled_indices)} frames to NV12 YUV              ")

                # Save image info metadata
                info_file = os.path.join(output_dir_camera, "image_info.txt")
                with open(info_file, 'w') as f:
                    f.write(f"Format: NV12\n")
                    f.write(f"Resolution: {width}x{height}\n")
                    f.write(f"Frame count: {frames_written}\n")
                    f.write(f"Frame size: {frame_size} bytes\n")
                    f.write(f"Sample rate: {sample_hz} Hz\n")

                # Clean up temporary H.264 file
                os.remove(h264_file)

            except Exception as e:
                print(f"    ✗ Error: {e}")
                import traceback
                traceback.print_exc()

    # Convert H.264 to JPEG images with frame sampling
    if output_format == 'jpeg':
        print("\n\nConverting H.264 to JPEG images...")
        for camera_name in camera_topics.values():
            if camera_name not in temp_h264_files:
                continue

            h264_file = temp_h264_files[camera_name]
            output_dir_camera = output_files[camera_name]

            if not os.path.exists(h264_file):
                print(f"  - {camera_name}: H.264 file not found")
                continue

            ts_list = timestamps.get(camera_name, [])
            if not ts_list:
                print(f"  - {camera_name}: No timestamps found")
                continue

            sampled_indices = sample_frames_by_hz(ts_list, sample_hz)

            print(f"\n  {camera_name}: Total frames: {len(ts_list)}")
            print(f"    Sampling at {sample_hz} Hz -> {len(sampled_indices)} frames selected")

            if not sampled_indices:
                print(f"    No frames to process")
                continue

            try:
                if len(ts_list) > 1:
                    time_diffs = [ts_list[i + 1] - ts_list[i] for i in range(len(ts_list) - 1)]
                    avg_interval = sum(time_diffs) / len(time_diffs)
                    actual_fps = 1.0 / avg_interval if avg_interval > 0 else 20.0
                else:
                    actual_fps = 20.0

                select_expr = '+'.join([f'eq(n,{idx})' for idx in sampled_indices])

                print(f"    Decoding H.264 to JPEG...")
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-v", "error",
                    "-r", str(actual_fps),
                    "-i", h264_file,
                    "-vf", f"select='{select_expr}'",
                    "-vsync", "0",
                    "-q:v", "2",
                    os.path.join(output_dir_camera, f"{camera_name}_%04d.jpeg")
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    jpeg_files = [f for f in os.listdir(output_dir_camera) if f.endswith('.jpeg')]
                    print(f"    ✓ Converted {len(jpeg_files)} frames to JPEG")
                else:
                    print(f"    ✗ ffmpeg failed: {result.stderr[:200]}")

                os.remove(h264_file)

            except Exception as e:
                print(f"    ✗ Error: {e}")
                import traceback
                traceback.print_exc()

    print("\n\nExtraction complete:")
    elapsed_time = time.time() - start_time
    print(f"Total time: {elapsed_time:.2f}s")
    for camera_name in camera_topics.values():
        if camera_name in output_files:
            output_path = output_files[camera_name]
            count = message_counts.get(camera_name, 0)

            if output_format in ('yuv', 'jpeg'):
                if os.path.exists(output_path):
                    ext = '.yuv' if output_format == 'yuv' else '.jpeg'
                    label = 'NV12 YUV' if output_format == 'yuv' else 'JPEG'
                    files = [f for f in os.listdir(output_path) if f.endswith(ext)]
                    print(f"  - {camera_name}: {len(files)} {label} images in {output_path}")
            else:
                # For H.264, output_path is a file
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(
                        f"  - {camera_name}: {count} frames, {file_size / 1024 / 1024:.2f} MB"
                    )

    # Generate MP4 with correct framerate from exposure_time
    if output_format == 'mp4':
        print("\nGenerating MP4 files with correct framerate...")
        for camera_name in camera_topics.values():
            if camera_name in output_files and timestamps.get(camera_name):
                h264_file = output_files[camera_name]
                mp4_file = h264_file.replace(".h264", ".mp4")

                ts_list = timestamps[camera_name]
                if len(ts_list) > 1:
                    time_diffs = [
                        ts_list[i + 1] - ts_list[i] for i in range(len(ts_list) - 1)
                    ]
                    avg_interval = sum(time_diffs) / len(time_diffs)
                    actual_fps = 1.0 / avg_interval if avg_interval > 0 else 20.0

                    print(f"\n  {camera_name}:")
                    print(f"    FPS: {actual_fps:.2f} Hz")
                    print(f"    Avg interval: {avg_interval*1000:.2f} ms")

                    try:
                        cmd = [
                            "ffmpeg",
                            "-y",
                            "-r",
                            str(actual_fps),
                            "-i",
                            h264_file,
                            "-c:v",
                            "copy",
                            "-r",
                            str(actual_fps),
                            mp4_file,
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            print(f"    ✓ MP4: {mp4_file}")
                            # Update output_files to point to MP4
                            output_files[camera_name] = mp4_file
                        else:
                            print(f"    ✗ ffmpeg failed: {result.stderr[:200]}")
                    except Exception as e:
                        print(f"    ✗ Error: {e}")

    return output_files


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description='Extract H.264/YUV data from ROS bag files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Extract all cameras as H.264
  python bag_helper.py data.bag -o ./output

  # Extract all cameras as MP4
  python bag_helper.py data.bag -o ./output -f mp4

  # Extract specific cameras as YUV images (default 1 fps)
  python bag_helper.py data.bag -o ./output -f yuv -c camera_front camera_rear

  # Extract YUV images at 5 fps
  python bag_helper.py data.bag -o ./output -f yuv --hz 5

  # Extract YUV images every 2 seconds (0.5 fps)
  python bag_helper.py data.bag -o ./output -f yuv --hz 0.5

  # Extract YUV images every 10 seconds (0.1 fps)
  python bag_helper.py data.bag -o ./output -f yuv --hz 0.1

  # Extract JPEG images at 1 fps (named FrontWide_0001.jpeg, ...)
  python bag_helper.py data.bag -o ./output -f jpeg

  # Extract JPEG images at 5 fps for specific cameras
  python bag_helper.py data.bag -o ./output -f jpeg --hz 5 -c FrontWide

  # Extract single camera as H.264
  python bag_helper.py data.bag -c camera_left
        '''
    )

    parser.add_argument('bag_path', help='Path to the ROS bag file')
    parser.add_argument('-o', '--output-dir', dest='output_dir',
                        help='Output directory (defaults to bag file directory)')
    parser.add_argument('-f', '--format', dest='output_format',
                        choices=['h264', 'mp4', 'yuv', 'jpeg'], default='h264',
                        help='Output format: h264 (raw stream), mp4 (video file), yuv (NV12 image sequence), or jpeg (JPEG image sequence)')
    parser.add_argument('-c', '--cameras', dest='camera_names', nargs='+',
                        help='Camera names to process (space-separated). If not specified, all cameras will be processed.')
    parser.add_argument('--hz', type=float, default=1.0,
                        help='Sampling rate in Hz for YUV/JPEG output (frames per second). Default: 1.0 (1 frame per second). Only applies when -f yuv or -f jpeg.')

    args = parser.parse_args()

    # Validate bag file exists
    if not os.path.exists(args.bag_path):
        print(f"Error: Bag file not found: {args.bag_path}")
        sys.exit(1)

    # Process the bag
    output_files = extract_h264_from_bag(
        bag_path=args.bag_path,
        output_dir=args.output_dir,
        camera_names=args.camera_names,
        output_format=args.output_format,
        sample_hz=args.hz
    )

    if output_files:
        print("\nSuccess:")
        for camera_name, file_path in output_files.items():
            print(f"  {camera_name}: {file_path}")
    else:
        print("\nFailed to extract files")
        sys.exit(1)


if __name__ == "__main__":
    main()
