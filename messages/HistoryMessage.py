import socketUtils

async def handle_HistoryMessage(reader, writer, message):
    content = message["content"]
    id = list(content.keys())[0]
    type = list(content[id].keys())[0]
    value = content[id][type]

    writer.game.add_reward(id, type, value)

    await socketUtils.send_message_to_multiple_writers(message, writer.game.writers)