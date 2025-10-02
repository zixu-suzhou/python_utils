#!/usr/bin/env python3
"""
ROS Bag H.264 Video Extractor

从ROS bag文件中提取H.264视频数据，按话题中的相机名称保存为独立的.h264文件。
话题格式：/C/Camera/xxx，其中xxx为相机名称。
消息类型：mtc/CameraImage，数据在imageData字段中。
"""

import os
import sys


def extract_h264_from_bag(bag_path, output_dir=None):
    """
    从bag文件中提取H.264数据并保存为多个.h264文件

    Args:
        bag_path: bag文件的路径
        output_dir: 输出目录，默认为bag文件所在目录

    Returns:
        dict: 提取的相机及其文件路径字典
    """
    if not os.path.exists(bag_path):
        print(f"错误: bag文件不存在: {bag_path}")
        return {}

    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(bag_path))
        if not output_dir:
            output_dir = '.'
    else:
        os.makedirs(output_dir, exist_ok=True)

    print(f"正在读取bag文件: {bag_path}")

    # 导入rosbag并添加lz4支持
    try:
        import lz4.frame

        # 创建一个roslz4模块的替代品
        class FakeRosLZ4:
            @staticmethod
            def decompress(data):
                return lz4.frame.decompress(data)

        # 将fake模块注入到sys.modules（在导入rosbag之前）
        import sys
        sys.modules['roslz4'] = FakeRosLZ4()

        # 现在导入rosbag，它会检测到roslz4并启用lz4支持
        import rosbag

        print(f"已添加LZ4解压支持 (found_lz4={rosbag.bag.found_lz4})")

    except ImportError as e:
        print(f"错误: 请安装所需库: {e}")
        print("安装命令: pip install bagpy lz4")
        return {}

    # 打开bag文件
    try:
        bag = rosbag.Bag(bag_path, 'r', chunk_threshold=256*1024*1024, allow_unindexed=True)
    except Exception as e:
        print(f"错误: 无法打开bag文件: {e}")
        import traceback
        traceback.print_exc()
        return {}

    # 获取所有话题
    try:
        info = bag.get_type_and_topic_info()
        all_topics = info[1].keys()
        print(f"\n总共发现 {len(all_topics)} 个话题")
    except Exception as e:
        print(f"错误: 无法读取话题信息: {e}")
        bag.close()
        return {}

    # 查找相机话题
    camera_topics = {}
    for topic in all_topics:
        if topic.startswith('/C/Camera/'):
            camera_name = topic.split('/')[-1]
            camera_topics[topic] = camera_name

    if not camera_topics:
        print("警告: 未找到符合格式 /C/Camera/xxx 的话题")
        bag.close()
        return {}

    print(f"\n找到 {len(camera_topics)} 个相机话题:")
    for topic, camera_name in camera_topics.items():
        print(f"  - {topic} -> {camera_name}")

    # 创建输出文件
    output_files = {}
    file_handles = {}
    message_counts = {}

    for topic, camera_name in camera_topics.items():
        output_file = os.path.join(output_dir, f"{camera_name}.h264")
        output_files[camera_name] = output_file
        file_handles[topic] = open(output_file, 'wb')
        message_counts[camera_name] = 0
        print(f"创建输出文件: {output_file}")

    # 读取消息并提取数据
    print("\n正在提取H.264数据...")

    try:
        for topic, msg, t in bag.read_messages(topics=list(camera_topics.keys())):
            camera_name = camera_topics[topic]

            # mtc/CameraImage消息，数据在imageData字段中
            data = None

            if hasattr(msg, 'imageData'):
                # mtc/CameraImage.imageData字段
                data = bytes(msg.imageData)
            elif hasattr(msg, 'data'):
                # 其他可能的格式
                data = bytes(msg.data)
            elif hasattr(msg, 'image') and hasattr(msg.image, 'data'):
                data = bytes(msg.image.data)

            if data and len(data) > 0:
                file_handles[topic].write(data)
                message_counts[camera_name] += 1

                if message_counts[camera_name] % 100 == 0:
                    print(f"  {camera_name}: {message_counts[camera_name]} 帧", end='\r')

    except Exception as e:
        print(f"\n错误: 读取消息时出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭所有文件
        for fh in file_handles.values():
            fh.close()
        bag.close()

    print("\n\n提取完成:")
    for camera_name in camera_topics.values():
        if camera_name in output_files:
            output_file = output_files[camera_name]
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                count = message_counts.get(camera_name, 0)
                print(f"  - {camera_name}: {count} 帧, 文件大小: {file_size / 1024 / 1024:.2f} MB")

    return output_files


def main():
    """命令行主函数"""
    if len(sys.argv) < 2:
        print("用法: python bag_helper.py <bag_file_path> [output_directory]")
        print("\n示例:")
        print("  python bag_helper.py data.bag")
        print("  python bag_helper.py data.bag ./output")
        sys.exit(1)

    bag_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    output_files = extract_h264_from_bag(bag_path, output_dir)

    if output_files:
        print("\n成功提取H.264文件:")
        for camera_name, file_path in output_files.items():
            print(f"  {camera_name}: {file_path}")
    else:
        print("\n未能提取任何H.264文件")
        sys.exit(1)


if __name__ == "__main__":
    main()
