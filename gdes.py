import struct

class GDES:
    def __init__(self, key: bytes, num_rounds: int = 16, block_size: int = 16):
        """
        Ingrid Schaumüller-Bichl's Generalized DES (G-DES) Implementation
        block_size: 16 bytes (128 bits) -> divided into a = 4 subblocks of 4 bytes (32 bits) each.
        key: 8 bytes (64 bits) -> expanded to subkeys.
        """
        self.num_rounds = num_rounds
        self.block_size = block_size
        self.a = block_size // 4  # Number of 32-bit subblocks
        assert len(key) >= 8, "G-DES Key must be at least 8 bytes (64 bits)"
        self.subkeys = self._generate_subkeys(key[:8])

    def _generate_subkeys(self, key_bytes: bytes) -> list:
        # Expand 64-bit key into num_rounds of 32-bit subkeys
        subkeys = []
        key_val = struct.unpack(">Q", key_bytes)[0]
        for i in range(self.num_rounds):
            # Use modulo 64 to keep the bit-rotation shift safe and positive [0, 63]
            shift = (i * 5) % 64
            if shift == 0:
                rotated = key_val
            else:
                rotated = ((key_val << shift) | (key_val >> (64 - shift))) & 0xFFFFFFFFFFFFFFFF
            
            subkeys.append(rotated & 0xFFFFFFFF)  # Extract lower 32 bits
        return subkeys

    def _f_function(self, subblock: int, subkey: int) -> int:
        # Feistel-like round F-function operating on 32 bits
        x = subblock ^ subkey
        # Mix bits (Multiplication with odd constant and rotation)
        x = (x * 0x01000193) & 0xFFFFFFFF
        x = ((x << 15) | (x >> 17)) & 0xFFFFFFFF
        return x

    def _pad(self, data: bytes) -> bytes:
        # PKCS7 Padding to fit block_size boundaries
        pad_len = self.block_size - (len(data) % self.block_size)
        return data + bytes([pad_len] * pad_len)

    def _unpad(self, data: bytes) -> bytes:
        pad_len = data[-1]
        assert 1 <= pad_len <= self.block_size, "Invalid padding values"
        return data[:-pad_len]

    def _encrypt_block(self, block: bytes) -> bytes:
        subblocks = list(struct.unpack(f">{self.a}I", block))
        
        for i in range(self.num_rounds):
            rightmost = subblocks[-1]
            temp = self._f_function(rightmost, self.subkeys[i])
            
            # XOR temp with all other subblocks (G-DES characteristic)
            for j in range(self.a - 1):
                subblocks[j] ^= temp
                
            # Cyclic rotate right: B_0 becomes rightmost, rest shift right
            subblocks = [rightmost] + subblocks[:-1]
            
        return struct.pack(f">{self.a}I", *subblocks)

    def _decrypt_block(self, block: bytes) -> bytes:
        subblocks = list(struct.unpack(f">{self.a}I", block))
        
        for i in range(self.num_rounds - 1, -1, -1):
            # Cyclic rotate left (inverse of encryption rotation)
            rightmost = subblocks[0]
            subblocks = subblocks[1:] + [rightmost]
            
            temp = self._f_function(rightmost, self.subkeys[i])
            
            # XOR temp with other subblocks to recover original states
            for j in range(self.a - 1):
                subblocks[j] ^= temp
                
        return struct.pack(f">{self.a}I", *subblocks)

    def encrypt(self, plaintext: bytes) -> bytes:
        padded = self._pad(plaintext)
        ciphertext = bytearray()
        for i in range(0, len(padded), self.block_size):
            block = padded[i:i+self.block_size]
            ciphertext.extend(self._encrypt_block(block))
        return bytes(ciphertext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        assert len(ciphertext) % self.block_size == 0, "Ciphertext length must match block boundaries"
        plaintext = bytearray()
        for i in range(0, len(ciphertext), self.block_size):
            block = ciphertext[i:i+self.block_size]
            plaintext.extend(self._decrypt_block(block))
        return self._unpad(bytes(plaintext))