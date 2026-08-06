import time
import socketUtils

async def handle_FireMessage(reader, writer, message):
    game = getattr(writer, "game", None)
    if game is None or not game.gameStarted or not game.turnStarted:
        return
    if game.playerOrder[game.currentPlayerTurn] != writer.userId:
        return
    if game.turnTimeLeft > 5000:
        game.turnTimeLeft = 5000 # TimeAfterFiring in config
    await socketUtils.send_message_to_multiple_writers(message, game.writers)
