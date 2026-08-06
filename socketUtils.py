import asyncio
import json
import struct

from config import MAX_FRAME_BYTES, XOR_KEY


def xor_encrypt(message_bytes):
    encrypted = bytearray()
    for i, byte in enumerate(message_bytes):
        encrypted.append(byte ^ XOR_KEY[i % len(XOR_KEY)])
    return encrypted

async def send_message_to_multiple_writers(message, writers):
    if message["t"] != 1:
        print("Send message " + json.dumps(message))
    await asyncio.gather(
        *(send_message(message, writer) for writer in list(writers)),
        return_exceptions=True,
    )

async def send_message(message, writer):
    message_str = json.dumps(message)
    message_bytes = message_str.encode('utf-8')
    # XOR encrypt
    encrypted_bytes = xor_encrypt(message_bytes)
    if len(encrypted_bytes) > MAX_FRAME_BYTES:
        raise ValueError("Refusing to send an oversized frame")
    # Prefix with 4-byte length
    length_prefix = struct.pack('>I', len(encrypted_bytes))  # big-endian unsigned int
    # 4. Send to client
    if not writer.is_closing():
        writer.write(length_prefix + encrypted_bytes)
        await writer.drain()
