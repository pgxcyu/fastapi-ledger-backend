# app/core/crypto_sm2.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import re
from typing import Literal, Optional, Tuple, Union

from gmssl.sm2 import CryptSM2

Order = Literal["C1C3C2", "C1C2C3", "auto"]
C1Prefix = Literal["no04", "with04"]
HEX_RE = re.compile(r'^[0-9a-fA-F]+$')

# -------- helpers --------
def _clean_hex(s: str) -> str:
    h = (s or "").strip().strip('"').strip("'").replace(" ", "").replace("\n", "").replace("\r", "")
    if h.startswith(("0x", "0X")): h = h[2:]
    if len(h) % 2 != 0 or not HEX_RE.fullmatch(h):
        raise ValueError(f"invalid hex: len={len(h)}")
    return h

def normalize_pubkey_128(pub128_or_04xx: str) -> str:
    """返回 128 hex 的 X||Y（去掉可能的 04 前缀）"""
    h = _clean_hex(pub128_or_04xx)
    return h[2:] if h.startswith("04") else h

def gen_sm2_keypair() -> Tuple[str, str]:
    """生成 SM2 密钥对 (priv64, pub128)"""
    sm2c = CryptSM2(public_key='', private_key='')
    n = int(sm2c.ecc_table['n'], 16)
    # Generate d in [1, n-1]
    while True:
        d = int.from_bytes(os.urandom(32), 'big') % n
        if 1 <= d <= n - 1:
            break
    priv = f"{d:064x}".upper()
    pub  = sm2c._kg(d, sm2c.ecc_table['g']).upper()  # X||Y (128 hex), NO '04'
    return priv, pub

def make_sm2(priv64: str, pub128_or_04xx: str, *, strict: bool = True) -> CryptSM2:
    """从 hex 构造 CryptSM2；strict=True 时校验公钥是否由私钥推导"""
    priv = _clean_hex(priv64)
    pub128 = normalize_pubkey_128(pub128_or_04xx)
    if len(priv) != 64 or len(pub128) != 128: raise ValueError("bad key length")
    sm2_tmp = CryptSM2(public_key="", private_key=priv)
    if strict:
        derived = sm2_tmp._kg(int(priv, 16), sm2_tmp.ecc_table["g"])
        if derived.lower() != pub128.lower():
            raise ValueError("keypair mismatch: PUBLIC not derived from PRIVATE")
    return CryptSM2(public_key=pub128, private_key=priv)

def _split_gmssl_cipher_to_c1c3c2(h: str) -> Tuple[str, str, str]:
    """gmssl.encrypt() → C1||C3||C2（C1 可能带 04），拆成 (c1_no04, c3, c2)"""
    if h.startswith("04"):
        c1_no04, tail = h[2:130], h[130:]
    else:
        c1_no04, tail = h[:128], h[128:]
    c3, c2 = tail[:64], tail[64:]
    return c1_no04, c3, c2

def _ensure_c1_with04_and_tail(h: str) -> Tuple[str, str]:
    """把输入（可能带/不带 04）规范为 (C1_with04, tail)"""
    if h.startswith("04"):
        c1_with04, tail = h[:130], h[130:]
    else:
        if len(h) < 128: raise ValueError("cipher too short for C1")
        c1_with04, tail = "04" + h[:128], h[128:]
    if len(tail) < 64: raise ValueError("cipher tail too short (need 64 for C3)")
    return c1_with04, tail

def _ensure_c1_no04_and_tail(h: str) -> Tuple[str, str]:
    """把输入（可能带/不带 04）规范为 (C1_no04, tail)"""
    if h.startswith("04"):
        c1_no04, tail = h[2:], h[128:]
    else:
        c1_no04, tail = h[:128], h[128:]
    if len(tail) < 64: raise ValueError("cipher tail too short (need 64 for C3)")
    return c1_no04, tail

# -------- encrypt (sm2 作为第一个参数) --------
def sm2_encrypt_hex(
    sm2: CryptSM2,
    plaintext: Union[str, bytes],
    *,
    order: Order = "C1C3C2",
    c1_prefix: C1Prefix = "no04",
) -> str:
    """
    可调顺序/前缀的加密：
      - order: 'C1C3C2'（默认）或 'C1C2C3'
      - c1_prefix: 'no04'（默认）或 'with04'
    返回 hex 字符串
    """
    pt = plaintext if isinstance(plaintext, bytes) else plaintext.encode("utf-8")
    h = sm2.encrypt(pt).hex()                 # gmssl 原始：C1||C3||C2（C1 可能带 04）
    c1_no04, c3, c2 = _split_gmssl_cipher_to_c1c3c2(h)

    # 组装顺序
    assembled = (c1_no04 + c3 + c2) if order == "C1C3C2" else (c1_no04 + c2 + c3)

    # C1 前缀
    if c1_prefix == "with04":
        assembled = "04" + assembled
    return assembled

def sm2_encrypt_c1c3c2_no04(sm2: CryptSM2, plaintext: Union[str, bytes]) -> str:
    """推荐给前端/接口：不带 04 的 C1C3C2"""
    return sm2_encrypt_hex(sm2, plaintext, order="C1C3C2", c1_prefix="no04")

def sm2_encrypt_c1c2c3_no04(sm2: CryptSM2, plaintext: Union[str, bytes]) -> str:
    """若前端库偏好 C1C2C3，用这个"""
    return sm2_encrypt_hex(sm2, plaintext, order="C1C2C3", c1_prefix="no04")

# -------- decrypt (sm2 作为第一个参数) --------
def _assemble_for_gmssl(h: str, order: Literal["C1C3C2", "C1C2C3"]) -> str:
    """组合 gmssl.decrypt() 需要的字节序：C1(不带04)||C3||C2 或 C1(不带04)||C2||C3"""
    c1_no04, tail = _ensure_c1_no04_and_tail(h)
    if order == "C1C3C2":
        c3, c2 = tail[:64], tail[64:]
    else:
        c3, c2 = tail[-64:], tail[:-64]
    return c1_no04 + c3 + c2

def sm2_decrypt_hex(
    sm2: CryptSM2,
    cipher_hex: str,
    *,
    order: Order = "auto",
    encoding: Optional[str] = "utf-8",
    errors: str = "strict",
):
    """
    解密：
      - 输入密文可带/不带 '04'
      - order: 'C1C3C2' / 'C1C2C3' / 'auto'（先 C1C3C2 再 C1C2C3）
      - encoding=None 时返回 bytes
    """
    h = _clean_hex(cipher_hex)
    tried = []
    orders = [order] if order != "auto" else ["C1C3C2", "C1C2C3"]
    last_err: Optional[Exception] = None

    for ord_ in orders:
        try:
            body_hex = _assemble_for_gmssl(h, ord_)
            pt = sm2.decrypt(bytes.fromhex(body_hex))
            return pt if encoding is None else pt.decode(encoding, errors=errors)
        except Exception as e:
            last_err = e
            tried.append(ord_)
    raise ValueError(f"SM2 decrypt failed; tried orders={tried}. last_error={last_err}")
