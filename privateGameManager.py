import socketUtils

waiting_rooms = []


def is_game_existing(game_name):
    for i in waiting_rooms:
        if i.game_name == game_name:
            return True
    return False


def get_waiting_room(game_name):
    for i in waiting_rooms:
        if i.game_name == game_name:
            return i
    return -1


class PrivateWaitingRoom:

    def __init__(self, writer, player, game_name):
        self.writers = []
        self.writers.append(writer)

        self.game_name = game_name

        self.players = []
        self.players.append(player)
        self.owner = player["id"]

        self.map = ""
        self.match_time = ""
        self.turn_time = ""

    async def join(self, writer, player):
        self.players.append(player)
        self.writers.append(writer)

        response = {"t": 30, "id": writer.userId, "players": self.players, "owner": self.owner}  # map, battle_time, turn_time
        await socketUtils.send_message_to_multiple_writers(response, self.writers)

    async def disconnectPlayer(self, writer):
        id = writer.userId
        if len(self.players) == 1:
            # Destroy room
            waiting_rooms.remove(self)
            return

        if id == self.owner:
            # Host left, destroy room
            waiting_rooms.remove(self)

        for player in self.players:
            if player["id"] == id:
                self.players.remove(player)
        self.writers.remove(writer)

        response = {"t": 30, "id": writer.userId, "players": self.players, "owner": self.owner}  # map, battle_time, turn_time
        await socketUtils.send_message_to_multiple_writers(response, self.writers)


async def update():
    for waiting_room in waiting_rooms:
        for writer in waiting_room.writers:
            if writer.is_closing():
                await waiting_room.disconnectPlayer(writer)
