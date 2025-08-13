# ======== 配置部分 ========
reloc_bin_path = "import_table.bin"     # 要写入的重定位表数据文件
target_file_path = "CySpringPlugin_dump_10_2.dll"        # 目标文件,先复制一份过来
write_offset = 0xB5000                # 目标文件内的写入位置（偏移）
# ==========================

# 读取 reloc_table.bin
with open(reloc_bin_path, "rb") as f:
    reloc_data = f.read()

# 把数据写入目标文件
with open(target_file_path, "r+b") as f:
    f.seek(write_offset)
    f.write(reloc_data)

print(f"已将 {len(reloc_data)} 字节写入 {target_file_path} 的 0x{write_offset:X} 位置")
