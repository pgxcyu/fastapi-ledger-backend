#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correct SM2 keypair generator using gmssl.
- Private key: random integer d in [1, n-1], 64 hex (uppercase)
- Public key: 128 hex (X||Y, uppercase), NO '04' prefix (that's only for uncompressed point encoding)
- Also prints a quick self-test: encrypt('kyle') -> decrypt -> 'kyle'
"""
import os, sys
from gmssl.sm2 import CryptSM2

def gen_sm2_keypair():
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

def validate_pair(priv_hex: str, pub_hex: str) -> bool:
    sm2c = CryptSM2(public_key='', private_key=priv_hex)
    derived_pub = sm2c._kg(int(priv_hex, 16), sm2c.ecc_table['g']).upper()
    return derived_pub == pub_hex.upper()

def self_test(priv_hex: str, pub_hex: str):
    sm2c = CryptSM2(public_key=pub_hex, private_key=priv_hex)
    pt = b'kyle'
    ct = sm2c.encrypt(pt)  # gmssl default: C1||C3||C2, C1 **without** '04'
    out = sm2c.decrypt(ct)
    return pt, ct.hex(), out

def main():
    priv, pub = gen_sm2_keypair()
    ok = validate_pair(priv, pub)
    pt, ct_hex, out = self_test(priv, pub)
    print("=== SM2 keypair (gmssl) ===")
    print("SM2_PRIVATE_KEY_NOLOGIN=", priv)
    print("SM2_PUBLIC_KEY_NOLOGIN=", pub, "  # 128 hex, NO '04'", sep='')
    print("PUB_FOR_FRONT=04" + pub, "     # if your frontend (sm-crypto) needs uncompressed '04'+X+Y", sep='')
    print("pair_valid=", ok)
    print("self_test.pt=", pt)
    print("self_test.ct_hex=", ct_hex, "(len=", len(ct_hex), ")", sep='')
    print("self_test.ok =", out == pt)

    # 可选：保存到文件
    if input("\n是否保存密钥对到文件？(y/n): ").lower() == 'y':
        with open("sm2_keys.txt", "w", encoding="utf-8") as f:
            f.write(f"SM2 密钥对\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\n私钥: {priv}\n")
            f.write(f"公钥: {pub}\n")
        print(f"密钥对已保存到 {os.path.abspath('sm2_keys.txt')}")

    if not ok or out != pt:
        sys.exit(1)

if __name__ == '__main__':
    main()
