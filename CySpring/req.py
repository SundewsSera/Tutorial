import ctypes

# 加载 DLL
dll_path = "./CySpringPlugin_dump_5.dll"  # 替换为你的 DLL 路径
lz4_dll = ctypes.cdll.LoadLibrary(dll_path)
print("加载DLL成功")
