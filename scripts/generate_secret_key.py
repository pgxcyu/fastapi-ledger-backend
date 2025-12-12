#!/usr/bin/env python3
"""
Windows环境下生成随机密钥的工具
用于替代openssl rand -hex 32命令
"""
import secrets
import sys

def generate_secret_key(length=32):
    """生成指定长度的随机十六进制密钥"""
    return secrets.token_hex(length)

if __name__ == "__main__":
    try:
        key_length = 32
        if len(sys.argv) > 1:
            key_length = int(sys.argv[1])
        
        secret_key = generate_secret_key(key_length)
        print(f"生成的密钥 ({key_length*2} 字符):")
        print(secret_key)
        print(f"\n请将此密钥复制到 .env.prod 文件的 SECRET_KEY 字段中")
        
    except Exception as e:
        print(f"生成密钥时出错: {e}")
        sys.exit(1)