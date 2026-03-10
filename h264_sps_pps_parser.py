#!/usr/bin/env python3
"""
H.264 SPS/PPS Parser
Parses and displays Sequence Parameter Set and Picture Parameter Set information from H.264 files
"""

import sys
import struct

class BitReader:
    """Simple bit reader for parsing H.264 bitstream"""
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_bits(self, n):
        """Read n bits"""
        result = 0
        for _ in range(n):
            byte_pos = self.pos // 8
            bit_pos = 7 - (self.pos % 8)
            if byte_pos < len(self.data):
                bit = (self.data[byte_pos] >> bit_pos) & 1
                result = (result << 1) | bit
            self.pos += 1
        return result

    def read_ue(self):
        """Read unsigned exp-golomb coded value"""
        leading_zeros = 0
        while self.read_bits(1) == 0:
            leading_zeros += 1
        if leading_zeros == 0:
            return 0
        return (1 << leading_zeros) - 1 + self.read_bits(leading_zeros)

    def read_se(self):
        """Read signed exp-golomb coded value"""
        ue = self.read_ue()
        if ue % 2 == 0:
            return -(ue // 2)
        return (ue + 1) // 2

def parse_sps(sps_data):
    """Parse SPS (Sequence Parameter Set)"""
    br = BitReader(sps_data[5:])

    result = {}

    # Profile and level
    result['profile_idc'] = sps_data[5]
    result['constraint_flags'] = sps_data[6]
    result['level_idc'] = sps_data[7]

    # Profile name
    profile_names = {
        66: 'Baseline',
        77: 'Main',
        88: 'Extended',
        100: 'High',
        110: 'High 10',
        122: 'High 4:2:2',
        244: 'High 4:4:4'
    }
    result['profile_name'] = profile_names.get(result['profile_idc'], f"Unknown ({result['profile_idc']})")
    result['level'] = result['level_idc'] / 10

    # seq_parameter_set_id
    br = BitReader(sps_data[8:])
    result['sps_id'] = br.read_ue()

    # For High profiles, read chroma format
    if result['profile_idc'] in [100, 110, 122, 244, 44, 83, 86, 118, 128]:
        chroma_format_idc = br.read_ue()
        result['chroma_format_idc'] = chroma_format_idc
        if chroma_format_idc == 3:
            result['separate_colour_plane_flag'] = br.read_bits(1)
        result['bit_depth_luma'] = br.read_ue() + 8
        result['bit_depth_chroma'] = br.read_ue() + 8
        result['qpprime_y_zero_transform_bypass_flag'] = br.read_bits(1)
        seq_scaling_matrix_present = br.read_bits(1)

    # log2_max_frame_num_minus4
    result['log2_max_frame_num_minus4'] = br.read_ue()
    result['max_frame_num'] = 2 ** (result['log2_max_frame_num_minus4'] + 4)

    # pic_order_cnt_type
    pic_order_cnt_type = br.read_ue()
    result['pic_order_cnt_type'] = pic_order_cnt_type

    if pic_order_cnt_type == 0:
        result['log2_max_pic_order_cnt_lsb_minus4'] = br.read_ue()

    # max_num_ref_frames
    result['max_num_ref_frames'] = br.read_ue()

    # gaps_in_frame_num_value_allowed_flag
    result['gaps_in_frame_num_allowed'] = br.read_bits(1)

    # Picture size
    pic_width_in_mbs_minus1 = br.read_ue()
    pic_height_in_map_units_minus1 = br.read_ue()

    result['width_in_mbs'] = pic_width_in_mbs_minus1 + 1
    result['height_in_mbs'] = pic_height_in_map_units_minus1 + 1
    result['width'] = result['width_in_mbs'] * 16
    result['height'] = result['height_in_mbs'] * 16

    # frame_mbs_only_flag
    result['frame_mbs_only_flag'] = br.read_bits(1)

    if not result['frame_mbs_only_flag']:
        result['mb_adaptive_frame_field_flag'] = br.read_bits(1)
        result['height'] *= 2

    # direct_8x8_inference_flag
    result['direct_8x8_inference_flag'] = br.read_bits(1)

    # Frame cropping
    frame_cropping_flag = br.read_bits(1)
    if frame_cropping_flag:
        crop_left = br.read_ue()
        crop_right = br.read_ue()
        crop_top = br.read_ue()
        crop_bottom = br.read_ue()

        crop_unit_x = 2
        crop_unit_y = 2
        if not result['frame_mbs_only_flag']:
            crop_unit_y = 4

        result['crop_left'] = crop_left
        result['crop_right'] = crop_right
        result['crop_top'] = crop_top
        result['crop_bottom'] = crop_bottom
        result['display_width'] = result['width'] - (crop_left + crop_right) * crop_unit_x
        result['display_height'] = result['height'] - (crop_top + crop_bottom) * crop_unit_y
    else:
        result['display_width'] = result['width']
        result['display_height'] = result['height']

    return result

def parse_pps(pps_data):
    """Parse PPS (Picture Parameter Set)"""
    br = BitReader(pps_data[5:])

    result = {}
    result['pps_id'] = br.read_ue()
    result['sps_id'] = br.read_ue()
    result['entropy_coding_mode_flag'] = br.read_bits(1)
    result['entropy_coding'] = 'CABAC' if result['entropy_coding_mode_flag'] else 'CAVLC'
    result['pic_order_present_flag'] = br.read_bits(1)
    result['num_slice_groups_minus1'] = br.read_ue()

    result['num_ref_idx_l0_active_minus1'] = br.read_ue()
    result['num_ref_idx_l1_active_minus1'] = br.read_ue()
    result['weighted_pred_flag'] = br.read_bits(1)
    result['weighted_bipred_idc'] = br.read_bits(2)
    result['pic_init_qp_minus26'] = br.read_se()
    result['pic_init_qs_minus26'] = br.read_se()
    result['chroma_qp_index_offset'] = br.read_se()
    result['deblocking_filter_control_present_flag'] = br.read_bits(1)
    result['constrained_intra_pred_flag'] = br.read_bits(1)
    result['redundant_pic_cnt_present_flag'] = br.read_bits(1)

    return result

def find_and_parse_h264(filename, show_all_sps_pps=False):
    """Find and parse SPS/PPS from H.264 file"""
    with open(filename, 'rb') as f:
        data = f.read()

    start_code = b'\x00\x00\x00\x01'
    idx = 0
    sps_list = []
    pps_list = []

    while idx < len(data) - 5:
        idx = data.find(start_code, idx)
        if idx == -1:
            break

        nalu_type = data[idx + 4] & 0x1F

        next_idx = data.find(start_code, idx + 4)
        if next_idx == -1:
            next_idx = len(data)

        nalu = data[idx:next_idx]

        if nalu_type == 7:
            sps_list.append((idx, nalu))
        elif nalu_type == 8:
            pps_list.append((idx, nalu))

        idx = next_idx

    print(f"File: {filename}")
    print(f"Found {len(sps_list)} SPS and {len(pps_list)} PPS\n")

    # Parse first or all SPS
    sps_to_parse = sps_list if show_all_sps_pps else sps_list[:1]
    for i, (offset, sps_data) in enumerate(sps_to_parse):
        print("="*70)
        print(f"SPS #{i} at offset {offset} ({len(sps_data)} bytes)")
        print("="*70)

        print(f"\nRaw hex: {' '.join(f'{b:02x}' for b in sps_data[:min(40, len(sps_data))])}")
        if len(sps_data) > 40:
            print("...")

        try:
            sps_info = parse_sps(sps_data)
            print(f"\nParsed Parameters:")
            print(f"  Profile: {sps_info['profile_name']} (profile_idc={sps_info['profile_idc']})")
            print(f"  Level: {sps_info['level']}")
            print(f"  SPS ID: {sps_info['sps_id']}")
            if 'chroma_format_idc' in sps_info:
                chroma_formats = {0: '4:0:0', 1: '4:2:0', 2: '4:2:2', 3: '4:4:4'}
                print(f"  Chroma Format: {chroma_formats.get(sps_info['chroma_format_idc'], 'Unknown')}")
                print(f"  Bit Depth: {sps_info['bit_depth_luma']}bit (Luma), {sps_info['bit_depth_chroma']}bit (Chroma)")
            print(f"  Max Frame Number: {sps_info['max_frame_num']}")
            print(f"  POC Type: {sps_info['pic_order_cnt_type']}")
            print(f"  Max Reference Frames: {sps_info['max_num_ref_frames']}")
            print(f"  Resolution (coded): {sps_info['width']}x{sps_info['height']}")
            print(f"  Resolution (display): {sps_info['display_width']}x{sps_info['display_height']}")
            print(f"  Scan Type: {'Progressive' if sps_info['frame_mbs_only_flag'] else 'Interlaced'}")
            if 'crop_left' in sps_info:
                print(f"  Cropping: L={sps_info['crop_left']}, R={sps_info['crop_right']}, " +
                      f"T={sps_info['crop_top']}, B={sps_info['crop_bottom']}")
        except Exception as e:
            print(f"Error parsing SPS: {e}")
        print()

    # Parse first or all PPS
    pps_to_parse = pps_list if show_all_sps_pps else pps_list[:1]
    for i, (offset, pps_data) in enumerate(pps_to_parse):
        print("="*70)
        print(f"PPS #{i} at offset {offset} ({len(pps_data)} bytes)")
        print("="*70)

        print(f"\nRaw hex: {' '.join(f'{b:02x}' for b in pps_data)}")

        try:
            pps_info = parse_pps(pps_data)
            print(f"\nParsed Parameters:")
            print(f"  PPS ID: {pps_info['pps_id']}")
            print(f"  SPS ID: {pps_info['sps_id']} (references SPS #{pps_info['sps_id']})")
            print(f"  Entropy Coding: {pps_info['entropy_coding']}")
            print(f"  Num Ref Idx L0: {pps_info['num_ref_idx_l0_active_minus1'] + 1}")
            print(f"  Num Ref Idx L1: {pps_info['num_ref_idx_l1_active_minus1'] + 1}")
            print(f"  Weighted Prediction: {bool(pps_info['weighted_pred_flag'])}")
            print(f"  Initial QP: {pps_info['pic_init_qp_minus26'] + 26}")
            print(f"  Chroma QP Offset: {pps_info['chroma_qp_index_offset']}")
            print(f"  Deblocking Filter: {bool(pps_info['deblocking_filter_control_present_flag'])}")
            print(f"  Constrained Intra Pred: {bool(pps_info['constrained_intra_pred_flag'])}")
        except Exception as e:
            print(f"Error parsing PPS: {e}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 h264_sps_pps_parser.py <h264_file> [--all]")
        print("  --all: Show all SPS/PPS (not just first one)")
        sys.exit(1)

    h264_file = sys.argv[1]
    show_all = '--all' in sys.argv

    find_and_parse_h264(h264_file, show_all)
