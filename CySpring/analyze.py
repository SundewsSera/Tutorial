import struct

# ======== 配置部分 ========
file_path = r"CySpringPlugin_dump_8_1.dll"  # 你的PE文件路径
start_range = 0x7FFD6EA90000  # 范围起始值
end_range   = 0x7FFDA2EA8000  # 范围结束值
aligned_output_path = r"result_aligned.txt"   # 对齐结果
unaligned_output_path = r"result_unaligned.txt" # 非对齐结果
scan_start_offset = 0x1000  # 从这里开始扫描
# =========================

aligned_results = []
unaligned_results = []

with open(file_path, "rb") as f:
    data = f.read()

# 遍历文件，从 0x1000 开始
for offset in range(scan_start_offset, len(data) - 8 + 1):
    qword_bytes = data[offset:offset + 8]
    
    # 按 little-endian 解释为无符号64位整数
    value = struct.unpack("<Q", qword_bytes)[0]
    
    if start_range <= value <= end_range:
        if offset % 8 == 0:
            aligned_results.append((offset, value))
        else:
            aligned_results.append((offset, value))
            unaligned_results.append((offset, value))

# 保存对齐的结果
with open(aligned_output_path, "w", encoding="utf-8") as out:
    for offset, value in aligned_results:
        out.write(f"Offset: 0x{offset:08X} | Value: 0x{value:016X}\n")

# 保存不对齐的结果
with open(unaligned_output_path, "w", encoding="utf-8") as out:
    for offset, value in unaligned_results:
        out.write(f"Offset: 0x{offset:08X} | Value: 0x{value:016X}\n")

print(f"扫描完成：")
print(f"  对齐匹配项: {len(aligned_results)} -> {aligned_output_path}")
print(f"  非对齐匹配项: {len(unaligned_results)} -> {unaligned_output_path}")
