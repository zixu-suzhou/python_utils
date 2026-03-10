# ADCU H.264 编码优化 - 快速行动清单

## 🔴 立即修复（本周内）

### 问题 1: 码率过高 (50 Mbps)
**影响**: 存储空间紧张 (180 GB/天)，网络传输困难

**快速修复（无需改代码）:**
```c
// 编码器配置文件修改
max_num_ref_frames: 2 → 4      // 提升压缩效率
gop_size: 5 → 10                // 降低 I 帧比例
pic_init_qp: 26 → 28            // 轻微降低质量
```

**预期效果:**
- 码率: 50 Mbps → 35 Mbps (-30%)
- 存储: 180 GB/天 → 126 GB/天
- 质量: 几乎无感下降

**验证方法:**
```bash
# 1. 重新编码一段测试视频
# 2. 使用分析工具检查码率
bash ffmpeg_h264_analyzer.sh test_optimized.h264

# 3. 对比质量
python3 << 'EOF'
# 提取关键帧对比
import cv2
# ... 对比代码见评估报告附录 C
EOF
```

---

### 问题 2: 缺少时间戳信息
**影响**: 多摄像头无法精确同步，事件时间不准确

**快速修复:**
```c
// 在编码时添加时间戳 SEI
struct TimestampSEI {
    uint64_t capture_time_ns;   // 纳秒级时间戳
    uint32_t frame_sequence;    // 帧序列号
    uint8_t  camera_id;         // 摄像头 ID
};

// 每帧插入 SEI
// 具体实现见评估报告
```

**预期效果:**
- 多摄像头同步精度: < 10ms
- 事件回溯准确性: 100%

---

## 🟡 短期优化（1-2 周）

### 优化 1: 启用 VBR 码率控制
**当前**: 固定 QP (CQP)，码率波动大
**目标**: 平均码率控制，适配网络传输

**配置修改:**
```c
rc_mode: CQP → VBR
target_bitrate: 30 Mbps
max_bitrate: 40 Mbps
```

**效果:**
- 平均码率稳定在 30 Mbps
- 复杂场景允许 40 Mbps 峰值
- 简单场景降低到 20 Mbps

---

### 优化 2: 差异化多摄像头配置
**当前**: 所有摄像头 4K@50Mbps (系统总 300 Mbps)
**目标**: 根据重要性分级

**推荐配置:**
```yaml
FrontWide (主):     4K, 30 Mbps
FrontTele:          2K, 15 Mbps
WingFront (L/R):    1080p, 8 Mbps
WingRear (L/R):     1080p, 6 Mbps
Rear:               1080p, 8 Mbps
NearRange (4个):    720p, 3 Mbps

系统总带宽: 300 Mbps → 110 Mbps (-63%)
```

---

## 🟢 中期规划（1-2 个月）

### 规划 1: 场景自适应编码
```c
// 检测场景类型
if (scene == HIGHWAY) {
    qp = 30;  // 简单场景，降低质量
    gop = 30;
} else if (scene == CITY) {
    qp = 26;  // 复杂场景，提升质量
    gop = 15;
} else if (scene == NIGHT) {
    qp = 22;  // 夜间，最高质量
    gop = 10;
}
```

### 规划 2: 事件触发高质量
```c
// 正常驾驶
target_bitrate = 25 Mbps;
qp = 28;

// 检测到关键事件（急刹车、碰撞）
if (trigger_event) {
    target_bitrate = 50 Mbps;  // 提升码率
    qp = 22;                    // 提升质量
    gop = 5;                    // 更多关键帧
}
```

---

## 📊 对比表格

### 当前 vs 优化后

| 指标 | 当前配置 | 快速优化 | 完全优化 | 改善 |
|------|---------|----------|----------|------|
| **单摄像头码率** | 50 Mbps | 35 Mbps | 25-30 Mbps | -40% ~ -50% |
| **系统总带宽** | 300 Mbps | 210 Mbps | 110 Mbps | -63% |
| **每日存储 (8h)** | 180 GB | 126 GB | 66 GB | -63% |
| **质量损失** | 基准 | -5% | -10% | 可接受 |
| **延迟** | 150ms | 180ms | 200ms | +50ms |
| **同步精度** | 无 | < 10ms | < 5ms | ✓ |

---

## 🎯 推荐实施顺序

### Week 1: 参数优化
```bash
Day 1-2: 修改编码配置
Day 3-4: 测试验证
Day 5:   小批量部署
```

### Week 2-3: SEI 元数据
```bash
Week 2: 实现时间戳 SEI
Week 3: 测试多摄像头同步
```

### Week 4-6: VBR + 差异化配置
```bash
Week 4: VBR 码率控制
Week 5: 多摄像头差异化
Week 6: 系统集成测试
```

### Week 7-8: A/B 测试
```bash
50% 车辆新配置
50% 车辆旧配置
收集反馈和数据
```

---

## ⚠️ 注意事项

### 1. 质量验证
```bash
# 每次修改后必须验证
1. 主观质量: 人工查看关键帧
2. 客观指标: PSNR/SSIM
3. 感知算法: 检测准确率
4. 极端场景: 夜间、雨天、逆光
```

### 2. 回滚计划
```bash
# 如果出现问题，立即回滚
1. 保留旧配置备份
2. 准备快速回滚脚本
3. 监控关键指标
```

### 3. 监控指标
```bash
# 持续监控
- 编码器 CPU/GPU 使用率
- 温度和功耗
- 丢帧率
- 存储写入速度
- 网络上传成功率
```

---

## 📞 支持联系

如有问题，请联系：
- 视频编码团队
- ADCU 系统团队
- 测试验证团队

---

## 附：配置文件示例

### encoder_config.json (优化前)
```json
{
  "camera_fw": {
    "resolution": "3840x2160",
    "fps": 20,
    "profile": "high",
    "level": "5.1",
    "gop_size": 5,
    "max_ref_frames": 2,
    "qp": 26,
    "rc_mode": "cqp",
    "cabac": true
  }
}
```

### encoder_config.json (快速优化后)
```json
{
  "camera_fw": {
    "resolution": "3840x2160",
    "fps": 20,
    "profile": "high",
    "level": "5.1",
    "gop_size": 10,              // ← 修改
    "max_ref_frames": 4,          // ← 修改
    "qp": 28,                     // ← 修改
    "rc_mode": "vbr",             // ← 修改
    "target_bitrate": 30000,      // ← 新增 (kbps)
    "max_bitrate": 40000,         // ← 新增 (kbps)
    "cabac": true,
    "sei_timestamp": true         // ← 新增
  }
}
```

### encoder_config.json (完全优化后)
```json
{
  "camera_fw": {
    "resolution": "3840x2160",
    "fps": 20,
    "profile": "high",
    "level": "5.1",
    "gop_size": 15,
    "max_ref_frames": 4,
    "qp_range": [22, 32],         // ← 自适应 QP
    "rc_mode": "vbr",
    "target_bitrate": 25000,
    "max_bitrate": 35000,
    "cabac": true,
    "sei_timestamp": true,
    "sei_vehicle_state": true,    // ← 新增
    "adaptive_qp": true,          // ← 新增
    "scene_detection": true       // ← 新增
  },

  "camera_wfl": {
    "resolution": "1920x1080",    // ← 降低分辨率
    "fps": 20,
    "gop_size": 15,
    "max_ref_frames": 3,
    "qp_range": [26, 34],
    "rc_mode": "vbr",
    "target_bitrate": 8000,
    "max_bitrate": 12000,
    "cabac": true,
    "sei_timestamp": true
  }
  // ... 其他摄像头配置
}
```

---

## 总结

**关键要点:**
1. ✅ 当前配置基本合理，但码率过高
2. ⚠️ 缺少元数据和自适应功能
3. 🎯 优化后可节省 50-60% 存储和带宽
4. 📈 质量损失 < 10%，可接受

**立即行动:**
- 修改 3 个参数 (GOP, ref_frames, QP)
- 添加时间戳 SEI
- 启动测试验证

**预期收益:**
- 存储成本: -50%
- 网络成本: -50%
- 系统可扩展性: +100%
