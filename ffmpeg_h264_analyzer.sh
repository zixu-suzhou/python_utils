#!/bin/bash
# FFmpeg/FFprobe H.264 Analysis Tool

if [ $# -eq 0 ]; then
    echo "Usage: $0 <h264_file>"
    echo "Example: $0 video.h264"
    exit 1
fi

H264_FILE="$1"

if [ ! -f "$H264_FILE" ]; then
    echo "Error: File not found: $H264_FILE"
    exit 1
fi

echo "=========================================================================="
echo "H.264 File Analysis using FFmpeg/FFprobe"
echo "=========================================================================="
echo "File: $H264_FILE"
echo "Size: $(du -h "$H264_FILE" | cut -f1)"
echo ""

echo "=========================================================================="
echo "1. Stream Information (from SPS/PPS)"
echo "=========================================================================="
ffprobe -v error -select_streams v:0 \
  -show_entries stream=profile,level,codec_name,width,height,pix_fmt,color_range,refs,has_b_frames \
  -of default=noprint_wrappers=1 "$H264_FILE" 2>&1 | grep -v "libncursesw"

echo ""
echo "=========================================================================="
echo "2. Frame Type Statistics (first 100 frames)"
echo "=========================================================================="
echo "Analyzing frame types..."

FRAME_STATS=$(ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries frame=pict_type -read_intervals "%+#100" \
  -of csv=p=0 "$H264_FILE" 2>&1 | grep -v "libncursesw")

I_FRAMES=$(echo "$FRAME_STATS" | grep -c "I")
P_FRAMES=$(echo "$FRAME_STATS" | grep -c "P")
B_FRAMES=$(echo "$FRAME_STATS" | grep -c "B")
TOTAL=$((I_FRAMES + P_FRAMES + B_FRAMES))

echo "  I frames: $I_FRAMES / $TOTAL ($(awk "BEGIN {printf \"%.1f\", $I_FRAMES*100/$TOTAL}")%)"
echo "  P frames: $P_FRAMES / $TOTAL ($(awk "BEGIN {printf \"%.1f\", $P_FRAMES*100/$TOTAL}")%)"
echo "  B frames: $B_FRAMES / $TOTAL ($(awk "BEGIN {printf \"%.1f\", $B_FRAMES*100/$TOTAL}")%)"

if [ $I_FRAMES -gt 0 ]; then
    GOP_SIZE=$((TOTAL / I_FRAMES))
    echo "  Average GOP size: ~$GOP_SIZE frames"
fi

echo ""
echo "=========================================================================="
echo "3. Frame Sizes (first 15 frames)"
echo "=========================================================================="
echo "Frame# | Type | Key | Size (KB)"
echo "-------|------|-----|----------"

ffprobe -v error -select_streams v:0 \
  -show_entries frame=coded_picture_number,pict_type,key_frame,pkt_size \
  -read_intervals "%+#15" -of csv=p=0 "$H264_FILE" 2>&1 | \
  grep -v "libncursesw" | \
  awk -F',' '{
    key=$1
    size=$2
    type=$3
    frame=$4
    kb=size/1024
    key_str=(key==1?"Yes":"No ")
    printf "%6s | %4s | %3s | %8.1f\n", frame, type, key_str, kb
  }'

echo ""
echo "=========================================================================="
echo "4. NALU Type Detection"
echo "=========================================================================="
echo "Detecting NALU types in first few frames..."

ffmpeg -loglevel debug -i "$H264_FILE" -frames:v 3 -f null - 2>&1 | \
  grep "nal_unit_type" | head -20 | \
  grep -v "libncursesw" | \
  sed 's/.*nal_unit_type: //' | \
  sort | uniq -c | sort -rn

echo ""
echo "=========================================================================="
echo "5. Quality Metrics (first 10 frames)"
echo "=========================================================================="
echo "Frame# | Type | Mean(Y) | StdDev(Y)"
echo "-------|------|---------|----------"

ffmpeg -i "$H264_FILE" -vf "showinfo" -frames:v 10 -f null - 2>&1 | \
  grep "Parsed_showinfo" | \
  grep -v "libncursesw" | \
  awk '{
    # Extract frame number
    if (match($0, /n:[ ]*[0-9]+/)) {
      frame_str = substr($0, RSTART, RLENGTH)
      gsub(/n:[ ]*/, "", frame_str)
      frame = frame_str
    }

    # Extract type
    type = "?"
    if (match($0, /type:[IPB]/)) {
      type = substr($0, RSTART+5, 1)
    }

    # Extract mean (Y channel - first value in mean array)
    mean_val = "?"
    if (match($0, /mean:\[[0-9]+/)) {
      mean_str = substr($0, RSTART+6)
      if (match(mean_str, /[0-9]+/)) {
        mean_val = substr(mean_str, RSTART, RLENGTH)
      }
    }

    # Extract stdev (Y channel - first value in stdev array)
    stdev_val = "?"
    if (match($0, /stdev:\[[0-9.]+/)) {
      stdev_str = substr($0, RSTART+7)
      if (match(stdev_str, /[0-9.]+/)) {
        stdev_val = substr(stdev_str, RSTART, RLENGTH)
      }
    }

    printf "%6s | %4s | %7s | %8s\n", frame, type, mean_val, stdev_val
  }'

