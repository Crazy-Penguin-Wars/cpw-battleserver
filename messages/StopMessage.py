import socketUtils

async def handle_StopMessage(reader, writer, message):
    for writer in writer.game.writers:
        message2 = message.copy()
        message2["id"] = writer.userId
        await socketUtils.send_message(message2, writer)