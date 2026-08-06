async def handle_StartGameMessage(reader, writer, message):
    waiting_room = getattr(writer, "waiting_room", None)
    if waiting_room is None or waiting_room.owner != writer.userId:
        return
    await waiting_room.start_game()
