import time
import socketUtils

async def handle_DieMessage(reader, writer, message):
    die_time = time.time() * 1000
    respawn_time = die_time + 5000 # "TimeToRespawn" in config
    resume_time = die_time + 5000 # "TimeToResume" in config
    message["respawn_time"] = respawn_time
    message["resume_time"] = resume_time
    writer.game.addPlayerToRespawnQueue(message)

    await socketUtils.send_message_to_multiple_writers(message, writer.game.writers)