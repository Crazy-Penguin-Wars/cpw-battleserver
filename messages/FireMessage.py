import time
import socketUtils

async def handle_FireMessage(reader, writer, message):
    writer.game.turnTimeLeft = 5000 # TimeAfterFiring in config
    await socketUtils.send_message_to_multiple_writers(message, writer.game.writers)