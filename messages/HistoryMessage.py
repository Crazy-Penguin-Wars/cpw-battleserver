import socketUtils


async def handle_HistoryMessage(reader, writer, message):
    # Echo
    await socketUtils.send_message_to_multiple_writers(message, writer.game.writers)

    #if "statistics" in message["content"][writer.userId] and "turns" in message["content"][writer.userId]["statistics"]:
    #    walkmodemessage = {
    #        "t" : 8,
    #        "id": writer.game.playerOrder[writer.game.currentPlayerTurn]
    #    }
    #    await socketUtils.send_message_to_multiple_writers(walkmodemessage, writer.game.writers)
