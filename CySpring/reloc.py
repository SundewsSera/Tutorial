import re
import struct
from collections import defaultdict

# 输入/输出
input_txt = "result_aligned.txt"
output_bin = "reloc_table.bin"

# 常量
PAGE_SIZE = 0x1000
TYPE_DIR64 = 0xA  # IMAGE_REL_BASED_DIR64

# 读取 offsets（更稳健的解析）
offsets = []
pat = re.compile(r"Offset:\s*0x([0-9A-Fa-f]+)")
with open(input_txt, "r", encoding="utf-8") as f:
    for line in f:
        m = pat.search(line)
        if m:
            offsets.append(int(m.group(1), 16))

# 去重并按页分组
pages = defaultdict(set)
for off in offsets:
    page_rva = off & ~(PAGE_SIZE - 1)     # 页起始（4K对齐）
    page_off = off &  (PAGE_SIZE - 1)     # 页内偏移（12位）
    pages[page_rva].add(page_off)

# 生成重定位表
reloc_data = bytearray()

for page_rva in sorted(pages.keys()):
    # 构建本页的 TypeOffset 数组（每项2字节）
    entry_data = bytearray()
    for poff in sorted(pages[page_rva]):
        type_offset = (TYPE_DIR64 << 12) | poff  # 高4位类型，低12位页内偏移
        entry_data += struct.pack("<H", type_offset)

    # 4字节对齐：如果条目数为奇数，补一个WORD 0（ABSOLUTE）
    if (len(entry_data) % 4) != 0:
        entry_data += b"\x00\x00"  # IMAGE_REL_BASED_ABSOLUTE

    size_of_block = 8 + len(entry_data)  # 头8字节 + 条目区
    reloc_data += struct.pack("<II", page_rva, size_of_block)
    reloc_data += entry_data

with open(output_bin, "wb") as f:
    f.write(reloc_data)

print(f"OK: 生成 {output_bin}")
print(f"共 {len(offsets)} 个偏移，分布于 {len(pages)} 个页；"
      f"所有块已按4字节对齐。")
