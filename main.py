import asyncio
import json
import struct
import findGameManager
import gameManager
from messages import *
import privateGameManager
import socketUtils

XOR_KEY = [30,62,21,119,49,75,39,120,47,85,96,92,96,85,37,85,87,72,98,99,20,64,85,57,106,42,16,92,52,17,65,84,124,114,20,17,99,111,42,43,93,116,24,49,92,62,22,30,51,108,36,92,122,50,83,40,119,59,72,107,75,27,102,40,33,97,9,33,72,124,96,93,50,93,93,117,38,35,2,101,27,35,62,15,109,111,66,57,46,11,68,32,4,105,74,31,94,33,104,66,108,103,12,97,106,81,84,47,104,15,40,81,51,110,11,108,19,122,59,59,80,126,42,101,29,57,1,118,102,89,62,67,14,25,69,111,125,59,94,111,117,32,115,64,26,68,86,106,78,98,54,63,119,6,27,114,66,2,61,55,36,10,18,72,15,73,7,83,114,27,123,37,121,80,26,121,76,59,108,4,6,79,64,96,94,92,25,106,36,99,104,111,62,108,83,19,57,59,82,111,109,81,31,48,44,69,68,94,9,4,51,74,102,15,40,7,25,46,75,87,69,116,15,11,95,57,85,121,26,96,50,10,0,64,44,114,121,103,37,31,50,34,60,117,22,97,107,21,47,80,30,5,82,50,61,35,96,83,49,123,72,62,0,92,87,111,26,86,46,23,105,66,40,126,103,50,79,85,115,105,91,39,88,93,17,16,61,33,74,108,45,91,83,121,69,101,73,75,126,51,98,19,65,32,54,119,76,1,126,43,31,77,113,107,37,60,91,47,117,18,43,100,18,13,28,79,94,104,28,47,47,34,24,14,23,119,117,45,2,31,15,111,116,24,79,19]

CROSS_DOMAIN_POLICY = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">'
    '<cross-domain-policy>'
    '<allow-access-from domain="*" to-ports="*" />'
    '</cross-domain-policy>\0'
)

MESSAGES = {
    29: handle_ConnectMessage_MatchMaker,
    26: handle_ConnectMessage_BattleServer,
    15: handle_ClientReadyMessage,
    8: echo_message,
    14: handle_HistoryMessage,
    7: echo_message,
    13: echo_message,
    3: echo_message,
    12: echo_message,
    11: echo_message,
    10: handle_FireMessage,
    2: echo_message,
    9: echo_message,
    6: echo_message,
    4: echo_message,
    5: echo_message,
    18: echo_message,
    33: echo_message,
    20: echo_message,
    60: echo_message,
    32: handle_StartGameMessage,
    35: handle_DieMessage
}

async def handle_connection(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Connection from {addr}")
    try:
        # Read some bytes, enough to cover policy or length prefix
        peek_data = await asyncio.wait_for(reader.read(1024), timeout=5)
        if not peek_data:
            print(f"No data received from {addr}")
            return

        # Try to decode peek_data as UTF-8 (ignore errors)
        try:
            peek_message = peek_data.decode('utf-8', errors='ignore').strip('\0').strip()
        except Exception:
            peek_message = ""

        if peek_message == "<policy-file-request/>":
            print(f"Received policy file request from {addr}")
            writer.write(CROSS_DOMAIN_POLICY.encode('utf-8'))
            await writer.drain()
            print(f"Sent policy file to {addr}")
            # Close connection after sending policy
            return

        # Else: treat peek_data as start of XOR encrypted message stream

        # Since you already read some bytes, put them back into a buffer to process fully
        buffer = bytearray(peek_data)

        while True:
            # Need to read length prefix (4 bytes)
            while len(buffer) < 4:
                more = await reader.read(4096)
                if not more:
                    print(f"Connection closed by {addr}")
                    return
                buffer.extend(more)

            length = int.from_bytes(buffer[0:4], byteorder='big')
            buffer = buffer[4:]

            # Read full encrypted message
            while len(buffer) < length:
                more = await reader.read(4096)
                if not more:
                    print(f"Connection closed by {addr} (incomplete message)")
                    return
                buffer.extend(more)

            encrypted_msg = buffer[0:length]
            buffer = buffer[length:]

            # XOR decrypt
            decrypted_bytes = bytes(
                b ^ XOR_KEY[i % len(XOR_KEY)] for i, b in enumerate(encrypted_msg)
            )
            message = json.loads(decrypted_bytes.decode('utf-8'))
            print(f"Decrypted message from {addr}: {message}")

            message = json.loads(decrypted_bytes.decode('utf-8'))
            if message["t"] in MESSAGES:
                handler = MESSAGES[message["t"]]
                response = await handler(reader, writer, message)

                if response != None:
                    response_str = json.dumps(response)
                    response_bytes = response_str.encode('utf-8')
                    # XOR encrypt
                    encrypted_bytes = socketUtils.xor_encrypt(response_bytes)
                    # Prefix with 4-byte length
                    length_prefix = struct.pack('>I', len(encrypted_bytes))  # big-endian unsigned int
                    # 4. Send to client
                    writer.write(length_prefix + encrypted_bytes)
                    await writer.drain()
                    
                    print(f"Replied with: {response_str}")
                
            else:
                print("Message not handled")

    except asyncio.TimeoutError:
        print(f"Timeout waiting for data from {addr}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"Connection with {addr} closed.")

async def updateWorld():
    while True:
        await gameManager.update()
        await asyncio.sleep(0.0333)

async def updateWaitingRooms():
    while True:
        await privateGameManager.update()
        await asyncio.sleep(1)

async def updateMatchmaking():
    while True:
        await findGameManager.update()
        await asyncio.sleep(1)

async def main():
    server = await asyncio.start_server(handle_connection, '0.0.0.0', 5050)

    asyncio.create_task(updateWorld())
    asyncio.create_task(updateWaitingRooms())
    asyncio.create_task(updateMatchmaking())

    async with server:
        print("TCP server running on port 5050")
        await server.serve_forever()

asyncio.run(main())