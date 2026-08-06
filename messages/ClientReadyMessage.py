import gameManager
import socketUtils

async def handle_ClientReadyMessage(reader, writer, message):
    game = getattr(writer, "game", None)
    if game is not None and message.get("id") == writer.userId and (not game.gameStarted or not game.turnStarted):
        await game.playerReady(writer.userId)
