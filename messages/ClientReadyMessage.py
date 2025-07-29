import gameManager
import socketUtils

async def handle_ClientReadyMessage(reader, writer, message):
    if not writer.game.gameStarted or not writer.game.turnStarted:
        await writer.game.playerReady(message["id"])