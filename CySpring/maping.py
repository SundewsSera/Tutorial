# -*- coding: utf-8 -*-

# 输入文件路径
sample_file = "sample.txt"
symbol_file = "symbol.txt"
output_file = "map.txt"

# 1) 读取 symbol.txt，建立地址(int) -> 函数名 的映射
addr_to_name = {}
with open(symbol_file, "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        try:
            addr_int = int(parts[0], 16)  # 统一转换成整数
            func_name = parts[-1]
            addr_to_name[addr_int] = func_name
        except ValueError:
            continue  # 跳过非地址行

# 2) 读取 sample.txt，按顺序查找匹配的函数名
results = []
with open(sample_file, "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line:
            continue
        try:
            left, right = line.split("|")
            offset_hex = left.split(":")[1].strip()
            value_hex = right.split(":")[1].strip()
            offset_int = int(offset_hex, 16)
            value_int = int(value_hex, 16)
            func_name = addr_to_name.get(value_int, "Unknown")
            results.append(f"0x{offset_int:08X} -> 0x{value_int:016X} -> {func_name}")
        except ValueError:
            continue

# 3) 写入 TXT 文件
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"结果已保存到 {output_file}")
