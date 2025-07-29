import socketUtils

async def echo_message(reader, writer, message):
    await socketUtils.send_message_to_multiple_writers(message, writer.game.writers)