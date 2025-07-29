import socketUtils

async def handle_WalkModeMessage(reader, writer, message):
    await socketUtils.send_message_to_multiple_writers(message, writer.game.writers)