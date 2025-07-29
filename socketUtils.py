import json
import struct


XOR_KEY = [30,62,21,119,49,75,39,120,47,85,96,92,96,85,37,85,87,72,98,99,20,64,85,57,106,42,16,92,52,17,65,84,124,114,20,17,99,111,42,43,93,116,24,49,92,62,22,30,51,108,36,92,122,50,83,40,119,59,72,107,75,27,102,40,33,97,9,33,72,124,96,93,50,93,93,117,38,35,2,101,27,35,62,15,109,111,66,57,46,11,68,32,4,105,74,31,94,33,104,66,108,103,12,97,106,81,84,47,104,15,40,81,51,110,11,108,19,122,59,59,80,126,42,101,29,57,1,118,102,89,62,67,14,25,69,111,125,59,94,111,117,32,115,64,26,68,86,106,78,98,54,63,119,6,27,114,66,2,61,55,36,10,18,72,15,73,7,83,114,27,123,37,121,80,26,121,76,59,108,4,6,79,64,96,94,92,25,106,36,99,104,111,62,108,83,19,57,59,82,111,109,81,31,48,44,69,68,94,9,4,51,74,102,15,40,7,25,46,75,87,69,116,15,11,95,57,85,121,26,96,50,10,0,64,44,114,121,103,37,31,50,34,60,117,22,97,107,21,47,80,30,5,82,50,61,35,96,83,49,123,72,62,0,92,87,111,26,86,46,23,105,66,40,126,103,50,79,85,115,105,91,39,88,93,17,16,61,33,74,108,45,91,83,121,69,101,73,75,126,51,98,19,65,32,54,119,76,1,126,43,31,77,113,107,37,60,91,47,117,18,43,100,18,13,28,79,94,104,28,47,47,34,24,14,23,119,117,45,2,31,15,111,116,24,79,19]

def xor_encrypt(message_bytes):
    encrypted = bytearray()
    for i, byte in enumerate(message_bytes):
        encrypted.append(byte ^ XOR_KEY[i % len(XOR_KEY)])
    return encrypted

async def send_message_to_multiple_writers(message, writers):
    if message["t"] != 1:
        print("Send message " + json.dumps(message))
    message_str = json.dumps(message)
    message_bytes = message_str.encode('utf-8')
    # XOR encrypt
    encrypted_bytes = xor_encrypt(message_bytes)
    # Prefix with 4-byte length
    length_prefix = struct.pack('>I', len(encrypted_bytes))  # big-endian unsigned int
    # 4. Send to client
    for writer in writers:
        writer.write(length_prefix + encrypted_bytes)
    await writer.drain()

async def send_message(message, writer):
    message_str = json.dumps(message)
    message_bytes = message_str.encode('utf-8')
    # XOR encrypt
    encrypted_bytes = xor_encrypt(message_bytes)
    # Prefix with 4-byte length
    length_prefix = struct.pack('>I', len(encrypted_bytes))  # big-endian unsigned int
    # 4. Send to client
    writer.write(length_prefix + encrypted_bytes)
    await writer.drain()