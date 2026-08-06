import asyncio
import json
import struct
import findGameManager
import gameManager
from messages import *
import privateGameManager
import socketUtils
from config import MAX_FRAME_BYTES, READ_TIMEOUT_SECONDS, SERVER_HOST, ONLINE_PORT, XOR_KEY

CROSS_DOMAIN_POLICY = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">'
    '<cross-domain-policy>'
    '<allow-access-from domain="*" to-ports="*" />'
    '</cross-domain-policy>\0'
)

MESSAGES = {
    29: handle_ConnectMessage_MatchMaker, # ConnectMessage
    26: handle_ConnectMessage_BattleServer, # ConnectMessage
    15: handle_ClientReadyMessage, # ClientReady
    8: echo_message, # WalkMode
    14: handle_HistoryMessage, # History
    7: echo_message, # Move
    13: echo_message, # UseEmoticon
    3: echo_message, # Stop
    12: echo_message, # AimMode
    11: echo_message, # FireMode
    10: handle_FireMessage, # FireMessage
    2: echo_message, # Aim
    9: echo_message, # Emit
    6: echo_message, # ChangeWeapon
    4: echo_message, # Jump
    5: echo_message, # JumpFinished
    18: echo_message, # PurchaseMessage
    33: echo_message, # ChatMessage
    20: echo_message, # EndGameConfirmMessage
    60: echo_message, # ChickeningOut
    32: handle_StartGameMessage, # StartGame
    35: handle_DieMessage, # Die
    40: handle_RematchRequestMessage # RematchRequest
    # To-do:
    # 34: UseBooster
    # 36: AddBooster
    # 55: SimpleScript
    # 28: ChangeSettings
    # 37: EnableBoosters
    # 50: IngameBet
}

async def handle_connection(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Connection from {addr}")
    try:
        # Read some bytes, enough to cover policy or length prefix
        peek_data = await asyncio.wait_for(reader.read(1024), timeout=READ_TIMEOUT_SECONDS)
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
                more = await asyncio.wait_for(reader.read(4096), timeout=READ_TIMEOUT_SECONDS)
                if not more:
                    print(f"Connection closed by {addr}")
                    return
                buffer.extend(more)

            length = int.from_bytes(buffer[0:4], byteorder='big')
            buffer = buffer[4:]
            if length <= 0 or length > MAX_FRAME_BYTES:
                print(f"Invalid frame length from {addr}: {length}")
                return

            # Read full encrypted message
            while len(buffer) < length:
                more = await asyncio.wait_for(reader.read(4096), timeout=READ_TIMEOUT_SECONDS)
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
            if not isinstance(message, dict) or not isinstance(message.get("t"), int):
                print(f"Invalid message shape from {addr}")
                continue
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
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"Invalid message from {addr}: {exc}")
    except Exception as exc:
        print(f"Connection handler failed for {addr}: {exc}")
    finally:
        game = getattr(writer, "game", None)
        if game is not None and writer in game.writers:
            await game.disconnectPlayer(writer)
        else:
            await findGameManager.disconnect_writer(writer)
            await privateGameManager.disconnect_writer(writer)
        writer.close()
        await writer.wait_closed()
        print(f"Connection with {addr} closed.")

async def updateWaitingRooms():
    while True:
        await privateGameManager.update()
        await asyncio.sleep(1)

async def updateMatchmaking():
    while True:
        await findGameManager.update()
        await asyncio.sleep(1)

async def main():
    server = await asyncio.start_server(handle_connection, SERVER_HOST, ONLINE_PORT)

    asyncio.create_task(updateWaitingRooms())
    asyncio.create_task(updateMatchmaking())

    async with server:
        print(f"TCP server running on {SERVER_HOST}:{ONLINE_PORT}")
        await server.serve_forever()

asyncio.run(main())
