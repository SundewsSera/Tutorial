import os
import sys
import sqlite3
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import re

class GameFileDecryptor:
    def __init__(self):
        self.base_key = None
        self.db_path = None
        self.conn = None
        self.output_dir = "Output"
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
    def input_base_key(self):
        """获取并解析用户输入的baseKey"""
        while True:
            key_input = "53 2B 46 31 E4 A7 B9 47 3E 7C FB" #input("请输入baseKey（格式如：53 2B 46 31 E4 A7 B9 47 3E 7C FB）：\n")
            # 验证输入格式
            pattern = r'^([0-9A-Fa-f]{2} )+[0-9A-Fa-f]{2}$'
            if re.match(pattern, key_input):
                # 转换为字节数组
                self.base_key = bytes.fromhex(key_input.replace(' ', ''))
                print(f"baseKey已存储，长度：{len(self.base_key)}字节")
                break
            else:
                print("输入格式错误，请按照指定格式重新输入（空格分隔的十六进制值）")
    
    def select_database(self):
        """弹窗选择sqlite数据库文件"""
        print("选择sqlite数据库文件")
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        self.db_path = filedialog.askopenfilename(
            title="选择sqlite数据库文件",
            filetypes=[("SQLite数据库", "*.*")]
        )
        
        if not self.db_path:
            messagebox.showerror("错误", "未选择数据库文件")
            sys.exit(1)
    
    def verify_database(self):
        """验证数据库是否有效"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # 检查表"a"是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='a'")
            if not cursor.fetchone():
                raise Exception("数据库中不存在表'a'")
            
            # 检查字段"h"是否存在
            cursor.execute("PRAGMA table_info(a)")
            columns = [column[1] for column in cursor.fetchall()]
            if "h" not in columns:
                raise Exception("表'a'中不存在字段'h'")
            if "n" not in columns:
                raise Exception("表'a'中不存在字段'n'")
            if "c" not in columns:
                raise Exception("表'a'中不存在字段'c'")
            
            print("数据库验证成功")
            return True
            
        except Exception as e:
            messagebox.showerror("数据库错误", f"数据库无效：{str(e)}")
            if self.conn:
                self.conn.close()
            print("按任意键退出...")
            input()
            sys.exit(1)
    
    def select_files(self):
        """让用户选择文件或目录"""
        print("请按Enter选择单个或多个游戏文件，或输入其他内容选择目录")
        key = input()
        
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        file_paths = []
        
        if key == "":  # Enter键选择文件
            file_paths = filedialog.askopenfilenames(
                title="选择游戏文件",
                filetypes=[("游戏文件", "*.*"), ("所有文件", "*.*")]
            )
        else:  # 输入其他内容选择目录
            dir_path = filedialog.askdirectory(title="选择目录")
            if dir_path:
                # 遍历目录及其子目录下的所有文件
                for root_dir, _, files in os.walk(dir_path):
                    for file in files:
                        file_paths.append(os.path.join(root_dir, file))
        
        if not file_paths:
            messagebox.showinfo("提示", "未选择任何文件")
            return []
            
        return list(file_paths)
    
    def get_file_info_from_db(self, filename):
        """从数据库获取文件的n和c值"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT n, e FROM a WHERE h = ?", (filename,))
            result = cursor.fetchone()
            if result:
                return {
                    "n": result[0],
                    "c": result[1]
                }
            return None
        except Exception as e:
            print(f"查询数据库时出错：{str(e)}")
            return None
            
    def generate_final_key(self, c):
        """
        根据 base_key 和 int64 c 生成 final_key，完全对应 C++ AssetBundleStream 构造逻辑。
        返回长度 = len(base_key) * 8 的 bytearray，并打印 c 和 final_key。
        """
        # 将 int64 c 转为小端 8 字节
        c_bytes = c.to_bytes(8, byteorder='little', signed=True)
        
        # 打印 c 的十六进制表示
        print("c (int64):", c)
        print("c bytes (little-endian hex):", ' '.join(f"{b:02X}" for b in c_bytes))
        
        final_key = bytearray(len(self.base_key) * 8)
        
        # 索引指针 v7，模拟 C++ 里每次 XOR 的全局累加
        v7 = 0
        for i, bk_byte in enumerate(self.base_key):
            for j in range(8):
                # 对应 C++: keys[i*8 + j] = base_key[i] ^ c_bytes[v7 % 8]
                final_key[i*8 + j] = bk_byte ^ c_bytes[v7 % 8]
                v7 += 1

        # 打印 final_key 的十六进制表示
        print("final_key:", ' '.join(f"{b:02X}" for b in final_key))
        
        return final_key
    
    def decrypt_file(self, file_path, n, c):
        """
        解密文件
        1. 生成finalKey
        2. 跳过前256字节
        3. 用finalKey对剩余内容进行循环异或解密
        """
        try:
            with open(file_path, 'rb') as f:
                # 读取整个文件内容
                all_data = f.read()
            
            # 检查文件大小是否至少256字节
            if len(all_data) < 256:
                raise Exception("文件太小，小于256字节")
            
            # 跳过前256字节，获取需要解密的部分
            encrypted_data = all_data[256:]
            
            # 生成finalKey
            final_key = self.generate_final_key(c)
            key_length = len(final_key)
            if key_length == 0:
                raise Exception("生成的finalKey为空")
            
            # 进行循环异或解密
            decrypted_data = bytearray()
            for i, byte in enumerate(encrypted_data):
                # 全局索引 = 256 + i（匹配代码中的v12）
                global_index = 256 + i
                key_byte = final_key[global_index % key_length]  # 使用全局索引取模
                decrypted_data.append(byte ^ key_byte)
            
            # 将加密内容和前256字节合并
            decrypted_data = all_data[:256] + decrypted_data
            return decrypted_data
        except Exception as e:
            print(f"解密文件时出错：{str(e)}")
            return None
    
    def process_files(self, file_paths):
        """处理选择的所有文件"""
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            print(f"正在处理：{filename}")
            
            # 从数据库查询文件信息
            file_info = self.get_file_info_from_db(filename)
            if not file_info:
                print(f"警告：数据库中未找到文件 {filename} 的信息，跳过该文件")
                continue
            
            # 解密文件
            decrypted_data = self.decrypt_file(file_path, file_info["n"], file_info["c"])
            if decrypted_data is None:
                print(f"错误：文件 {filename} 解密失败")
                continue
            
            # 保存解密后的文件
            output_path = os.path.join(self.output_dir, filename)
            try:
                with open(output_path, 'wb') as f:
                    f.write(decrypted_data)
                print(f"{filename} 成功解密")
            except Exception as e:
                print(f"保存解密文件 {filename} 时出错：{str(e)}")
    
    def run(self):
        """运行解密工具的主流程"""
        # 1. 输入baseKey
        self.input_base_key()
        
        # 2. 选择并验证数据库
        self.select_database()
        self.verify_database()
        
        # 3. 选择文件或目录
        file_paths = self.select_files()
        if not file_paths:
            print("没有选择任何文件，程序终止")
            input()
            return
        
        # 4. 处理文件
        print(f"共选择了 {len(file_paths)} 个文件，开始解密...")
        self.process_files(file_paths)
        
        # 5. 清理资源
        if self.conn:
            self.conn.close()
        
        print("所有文件处理完毕")
        print("按任意键退出...")
        input()

if __name__ == "__main__":
    decryptor = GameFileDecryptor()
    decryptor.run()
