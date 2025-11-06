from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
import binascii

class SM4Util:
    def __init__(self, key: bytes):
        """
        初始化SM4工具类
        :param key: 密钥（16字节，128位）
        """
        if len(key) != 16:
            raise ValueError("SM4密钥必须为16字节（128位）")
        self.key = key
        self.sm4 = CryptSM4()  # 初始化SM4加密器

    def encrypt_cbc(self, plaintext: str, iv: bytes = None) -> tuple:
        """
        CBC模式加密
        :param plaintext: 明文（字符串）
        :param iv: 初始向量（16字节，默认自动生成随机值）
        :return: (加密后的数据hex, 初始向量hex)
        """
        # 初始化加密模式和密钥
        self.sm4.set_key(self.key, SM4_ENCRYPT)
        
        # 处理初始向量（IV）：必须16字节，默认随机生成
        if iv is None:
            iv = b'\x00' * 16  # 也可使用随机值：iv = os.urandom(16)，需确保解密时一致
        if len(iv) != 16:
            raise ValueError("CBC模式初始向量IV必须为16字节")
        
        # 明文转字节，CBC模式需手动填充（gmssl不自动处理填充）
        plaintext_bytes = plaintext.encode('utf-8')
        padded_data = self._pad(plaintext_bytes)
        
        # 加密并转为hex
        ciphertext = self.sm4.crypt_cbc(iv, padded_data)
        return binascii.b2a_hex(ciphertext).decode('utf-8'), binascii.b2a_hex(iv).decode('utf-8')

    def decrypt_cbc(self, ciphertext_hex: str, iv_hex: str) -> str:
        """
        CBC模式解密
        :param ciphertext_hex: 加密后的数据（hex字符串）
        :param iv_hex: 初始向量（hex字符串）
        :return: 解密后的明文
        """
        # 初始化解密模式和密钥
        self.sm4.set_key(self.key, SM4_DECRYPT)
        
        # 转换为字节
        ciphertext = binascii.a2b_hex(ciphertext_hex)
        iv = binascii.a2b_hex(iv_hex)
        
        if len(iv) != 16:
            raise ValueError("CBC模式初始向量IV必须为16字节")
        
        # 解密并去除填充
        decrypted_data = self.sm4.crypt_cbc(iv, ciphertext)
        plaintext_bytes = self._unpad(decrypted_data)
        
        return plaintext_bytes.decode('utf-8')

    def encrypt_ecb(self, plaintext: str) -> str:
        """ECB模式加密（不推荐，无IV，安全性低）"""
        self.sm4.set_key(self.key, SM4_ENCRYPT)
        plaintext_bytes = plaintext.encode('utf-8')
        padded_data = self._pad(plaintext_bytes)
        ciphertext = self.sm4.crypt_ecb(padded_data)
        return binascii.b2a_hex(ciphertext).decode('utf-8')

    def decrypt_ecb(self, ciphertext_hex: str) -> str:
        """ECB模式解密"""
        self.sm4.set_key(self.key, SM4_DECRYPT)
        ciphertext = binascii.a2b_hex(ciphertext_hex)
        decrypted_data = self.sm4.crypt_ecb(ciphertext)
        plaintext_bytes = self._unpad(decrypted_data)
        return plaintext_bytes.decode('utf-8')

    def _pad(self, data: bytes) -> bytes:
        """PKCS#7填充（gmssl需手动处理填充）"""
        block_size = 16
        pad_length = block_size - (len(data) % block_size)
        return data + bytes([pad_length] * pad_length)

    def _unpad(self, data: bytes) -> bytes:
        """去除PKCS#7填充"""
        pad_length = data[-1]
        return data[:-pad_length]