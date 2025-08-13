def append_zeros(file_path, num_zeros, output_path=None):
    # 如果不指定输出文件，则覆盖原文件
    if output_path is None:
        output_path = file_path

    # 读取原始数据
    with open(file_path, "rb") as f:
        data = f.read()

    # 在末尾追加 num_zeros 个 0x00
    data += b"\x00" * num_zeros

    # 保存到输出文件
    with open(output_path, "wb") as f:
        f.write(data)

    print(f"已在 {output_path} 末尾添加 {num_zeros} 个 0x00 字节。")


if __name__ == "__main__":
    # 示例：在 test.bin 末尾添加 100 个 0x00，并保存为 test_padded.bin
    append_zeros("CySpringPlugin_dump_10.dll", 8192, "CySpringPlugin_dump_10.dll")
