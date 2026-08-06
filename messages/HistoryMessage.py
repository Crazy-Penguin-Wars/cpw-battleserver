import socketUtils

async def handle_HistoryMessage(reader, writer, message):
    if getattr(writer, "game", None) is None or not isinstance(message.get("content"), dict):
        return
    content = message["content"]
    if len(content) != 1:
        return
    id = list(content.keys())[0]
    if id != writer.userId or not isinstance(content[id], dict) or len(content[id]) != 1:
        return
    type = list(content[id].keys())[0]
    value = content[id][type]

    if type not in {"coins", "cash", "experience", "score", "usedItems", "earnedItems"}:
        return
    writer.game.add_reward(id, type, value)

    await socketUtils.send_message_to_multiple_writers(message, writer.game.writers)
