import socketUtils

async def handle_RematchRequestMessage(reader, writer, message):
    game = writer.game
    if game.matchTimeLeft <= 0:
        await writer.game.requestRematch(writer.userId)