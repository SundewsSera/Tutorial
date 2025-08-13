#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_import_table.py

从一个包含 "Offset -> Value -> Function" 列表的文本文件中读取函数名（按顺序），
生成一个单一 DLL (kernel32.dll) 的导入表二进制块（PE32+ / x64 风格），
假设导入表的 RVA 在 0xB5000，IAT 的 RVA 在 0x00081000。

输出: import_table.bin
"""

import re
import struct
import sys
from pathlib import Path

# -------- 配置 --------
INPUT_FILE = "map.txt"         # 你的输入文件（包含每行 Offset -> Value -> Function）
OUTPUT_FILE = "import_table.bin" # 生成的导入表二进制
DLL_NAME = b"kernel32.dll\x00"   # 导入的 DLL 名
IMPORT_TABLE_RVA = 0xB5000       # 生成的导入表所在 RVA（如你指定的）
IAT_RVA = 0x00081000             # IAT 的 RVA（你已经给出的 IAT 起始位置）
# -----------------------


def parse_input(path):
    funcs = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            funcs.append(line.split(">")[2][1:])
    return funcs

def build_import_block(func_names, import_rva, iat_rva, dll_name_bytes):
    """
    构造导入表二进制块，返回 bytes。
    Layout (RVA 相对于 import_rva):
      0x00: IMAGE_IMPORT_DESCRIPTOR (kernel32)  (20 bytes)
      0x14: NULL IMAGE_IMPORT_DESCRIPTOR (终结)  (20 bytes)
      0x28: ILT (OriginalFirstThunk) entries   (8 * (n + 1))  # 最后有一个 0 终结项
      ...: IMAGE_IMPORT_BY_NAME entries (每个: WORD hint + name + 0)
      ...: DLL name 字符串
    NOTE: FirstThunk (IAT) 在 IMAGE_IMPORT_DESCRIPTOR 写成 iat_rva（32-bit）
    """
    n = len(func_names)
    # 1) sizes
    descriptors_count = 2  # 一个 descriptor + 一个全 0 终止
    descriptors_size = descriptors_count * 20  # 每个 IMAGE_IMPORT_DESCRIPTOR 20 字节
    ilt_entry_size = 8  # PE32+ 的 thunk 大小 8 字节
    ilt_size = ilt_entry_size * (n + 1)  # n entries + 1 个 0 结束

    # 2) 准备 IMAGE_IMPORT_BY_NAME 数据（先生成，记录每个函数的相对偏移）
    name_blob = bytearray()
    name_rva_list = []
    for func in func_names:
        # Hint 置 0，后跟 ASCII 名和 \0
        entry = struct.pack("<H", 0) + func.encode("ascii") + b"\x00"
        name_rva = import_rva + descriptors_size + ilt_size + len(name_blob)
        name_rva_list.append(name_rva)
        name_blob += entry

    # 3) dll name RVA（放在 name_blob 之后）
    dll_name_rva = import_rva + descriptors_size + ilt_size + len(name_blob)

    # 4) 构造 ILT（OriginalFirstThunk）: 每项是 8 字节，存放指向 IMAGE_IMPORT_BY_NAME 的 RVA（零拓展到 8 字节）
    ilt_blob = bytearray()
    for rva in name_rva_list:
        # 将 32-bit RVA 放入 8 字节字段（文件里通常是零拓展）
        ilt_blob += struct.pack("<Q", rva)
    # 结尾 null entry（8 字节零）
    ilt_blob += struct.pack("<Q", 0)

    # 5) 构造 IMAGE_IMPORT_DESCRIPTOR（kernel32） + null descriptor
    descriptors_blob = bytearray()
    # OriginalFirstThunk = RVA of ILT (32-bit)
    original_first_thunk_rva = import_rva + descriptors_size  # ILT 紧跟 descriptor array
    descriptors_blob += struct.pack("<I", original_first_thunk_rva)  # OriginalFirstThunk
    descriptors_blob += struct.pack("<I", 0)  # TimeDateStamp
    descriptors_blob += struct.pack("<I", 0)  # ForwarderChain
    descriptors_blob += struct.pack("<I", dll_name_rva)  # Name (RVA to "kernel32.dll\0")
    descriptors_blob += struct.pack("<I", iat_rva)  # FirstThunk -> IAT RVA (loader 写入该处)
    # null descriptor (全 20 字节 0)
    descriptors_blob += b"\x00" * 20

    # 6) 最终 blob 顺序：descriptors + ilt + name_blob + dll_name_bytes
    final = bytearray()
    final += descriptors_blob
    final += ilt_blob
    final += name_blob
    final += dll_name_bytes

    return bytes(final), {
        "descriptors_rva": import_rva,
        "original_first_thunk_rva": original_first_thunk_rva,
        "dll_name_rva": dll_name_rva,
        "ilt_rva": import_rva + descriptors_size,
        "names_rva_start": import_rva + descriptors_size + ilt_size,
        "size": len(final)
    }

def main():
    in_path = Path(INPUT_FILE)
    if not in_path.exists():
        print(f"输入文件 {INPUT_FILE} 不存在。请把包含 mapping 的文本放到 {INPUT_FILE}。")
        sys.exit(1)

    funcs = parse_input(in_path)
    if not funcs:
        print("未解析到任何函数名。请检查输入文件格式（例如：0x00081000 -> 0x00007FFDA1FC4A00 -> RtlCaptureContext）")
        sys.exit(1)

    # 构造导入表
    blob, info = build_import_block(funcs, IMPORT_TABLE_RVA, IAT_RVA, DLL_NAME)

    # 写文件
    with open(OUTPUT_FILE, "wb") as f:
        f.write(blob)

    # 输出信息，便于检查
    print(f"生成导入表二进制：{OUTPUT_FILE} （大小 {len(blob)} 字节）")
    print("布局信息（RVA）：")
    for k,v in info.items():
        if isinstance(v, int):
            print(f"  {k} = 0x{v:08X}")
    print("\n说明：")
    print("- IMAGE_IMPORT_DESCRIPTOR.FirstThunk(=IAT) 已设置为 IAT_RVA.")
    print("- OriginalFirstThunk 指向 ILT（在导入表块内部），ILT 项为指向 IMAGE_IMPORT_BY_NAME 的 RVA（64-bit field）")
    print("- 你需要把该二进制写入文件中对应的文件偏移（或注入到 PE 对应节的偏移），并确保 OptionalHeader.DataDirectory[IMPORT].VirtualAddress 指向 0x%X，Size 覆盖整个块。" % IMPORT_TABLE_RVA)
    print("- IAT 的内存页/节必须存在且可写，这样 loader 在加载时可以把真实函数地址写入 IAT（FirstThunk）")

if __name__ == "__main__":
    main()
