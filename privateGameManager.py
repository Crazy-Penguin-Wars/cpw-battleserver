import socketUtils
from config import MAX_PLAYERS_PER_GAME
import gameManager
import random
from config import (
    DEFAULT_BATTLE_TIME_SECONDS,
    DEFAULT_TURN_TIME_SECONDS,
    ONLINE_URL,
    ONLINE_PORT,
)

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
        if len(self.players) >= MAX_PLAYERS_PER_GAME:
            return False
        self.players.append(player)
        self.writers.append(writer)

        response = {"t": 30, "id": writer.userId, "players": self.players, "owner": self.owner}  # map, battle_time, turn_time
        await socketUtils.send_message_to_multiple_writers(response, self.writers)
        return True

    async def start_game(self):
        if len(self.players) < 2:
            return False

        players = list(self.players)
        random.shuffle(players)
        game = gameManager.Game(
            players,
            DEFAULT_BATTLE_TIME_SECONDS,
            DEFAULT_TURN_TIME_SECONDS,
            random.randint(-2147483648, 2147483647),
        )
        gameManager.active_games.append(game)
        message = {
            "t": 27,
            "host": ONLINE_URL,
            "port": ONLINE_PORT,
            "map": self.map or "test_level",
            "battle_time": game.matchTime,
            "turn_time": game.turnTime,
            "seed": game.seed,
            "practice_mode": False,
            "players": players,
        }
        await socketUtils.send_message_to_multiple_writers(message, self.writers)
        if self in waiting_rooms:
            waiting_rooms.remove(self)
        return True

    async def disconnectPlayer(self, writer):
        id = writer.userId
        if len(self.players) == 1:
            # Destroy room
            if self in waiting_rooms:
                waiting_rooms.remove(self)
            return

        if id == self.owner:
            # Host left, destroy room
            if self in waiting_rooms:
                waiting_rooms.remove(self)

        for player in list(self.players):
            if player["id"] == id:
                self.players.remove(player)
        if writer in self.writers:
            self.writers.remove(writer)

        response = {"t": 30, "id": writer.userId, "players": self.players, "owner": self.owner}  # map, battle_time, turn_time
        await socketUtils.send_message_to_multiple_writers(response, self.writers)


async def update():
    for waiting_room in list(waiting_rooms):
        for writer in list(waiting_room.writers):
            if writer.is_closing():
                await waiting_room.disconnectPlayer(writer)


async def disconnect_writer(writer):
    for waiting_room in list(waiting_rooms):
        if writer in waiting_room.writers:
            await waiting_room.disconnectPlayer(writer)
