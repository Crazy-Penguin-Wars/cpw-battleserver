import socketUtils

async def handle_RematchRequestMessage(reader, writer, message):
    game = getattr(writer, "game", None)
    if game is None:
        return
    if game.matchTimeLeft <= 0:
        await writer.game.requestRematch(writer.userId)
