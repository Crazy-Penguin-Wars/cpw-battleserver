import socketUtils

async def handle_StartGameMessage(reader, writer, message):
    message = {"t" : 27, "id": writer.userId, "host": "127.0.0.1", "port": 5050}
    await socketUtils.send_message_to_multiple_writers(message, writer.waiting_room.writers)