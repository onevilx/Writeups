import hashlib
import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 1. Provide the passphrase found via OSINT
PASSPHRASE = "leet_ctflocal_1337"

# 2. Derive the 256-bit AES key
key = hashlib.sha256(PASSPHRASE.encode()).digest()

# 3. Read the hex string from the JPEG (this is the data extracted from the COM marker)
# Note: You can extract this programmatically or simply copy it from a hex editor.
extracted_hex = "ae8021aa5e4357a9d386fe2794003206d3cb0b231ec461cf48f6538f92a7d197c7009d5ba117cc9154ab207f14db634409055923f39ed4f9489f961a9c308272"
extracted_bytes = binascii.unhexlify(extracted_hex)

# 4. Split the IV and the Ciphertext
iv = extracted_bytes[:16]
ciphertext = extracted_bytes[16:]

# 5. Decrypt using AES-CBC
cipher = AES.new(key, AES.MODE_CBC, iv)
padded_flag = cipher.decrypt(ciphertext)

# 6. Unpad and print the flag
flag = unpad(padded_flag, AES.block_size)
print("[+] Decrypted Flag:", flag.decode())
