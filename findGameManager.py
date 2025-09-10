import aiohttp
import random
import uuid
import time

import gameManager
import socketUtils

waiting_players = []
waiting_rooms = []
settings = {}
settings["estimated_player_count"] = 0
settings["next_player_count_update"] = time.time() + 60
settings["minimum_waiting_time"] = 20
settings["extra_waiting_time_when_new_player_found"] = 15
settings["accept_level_range"] = 100


class WaitingPlayer:
    def __init__(self, writer, player):
        self.writer = writer

        self.player = player
        self.waiting_start_time = time.time()
        self.waiting_room = None

class WaitingRoom:
    def __init__(self, writer, player):
        self.writers = []
        self.writers.append(writer)

        self.game_name = str(uuid.uuid4())

        self.players = []
        self.players.append(player)
        self.first_player = player

        self.extra_waiting_time = 0

    async def start_game(self):
        print("Creating game")

        battle_time = random.randint(1, 1) * 60
        turn_time = random.randint(10, 30)
        seed = random.randint(-2147483648, 2147483647)

        all_players = [x.player for x in self.players]
        random.shuffle(all_players)

        game = gameManager.Game(all_players, battle_time, turn_time, seed)
        gameManager.active_games.append(game)

        message = {"t": 27,
                   "host": "127.0.0.1",
                   "port": 5050,
                   "map": "test_level",
                   "battle_time": battle_time,
                   "turn_time": turn_time,
                   "seed": seed,
                   "practice_mode": False, 
                   "players": all_players}
        await socketUtils.send_message_to_multiple_writers(message, self.writers)

        for player in self.players:
            waiting_players.remove(player)
        waiting_rooms.remove(self)

    async def disconnectPlayer(self, writer):
        id = writer.userId
        if len(self.players) == 1:
            # Destroy room
            waiting_rooms.remove(self)
            return

        for player in self.players:
            if player.player["id"] == id:
                self.players.remove(player)
                waiting_players.remove(player)

                if self.first_player == player:
                    self.first_player = self.players[0]
                break

        self.writers.remove(writer)


def add_new_player_to_matchmaking(player, writer):
    new_player = WaitingPlayer(writer, player)
    waiting_players.append(new_player)


async def update():
    current_time = time.time()
    # Once per minute: get estimated player count from main server
    if current_time >= settings["next_player_count_update"]:
        settings["next_player_count_update"] = current_time + 60

        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:5055/status") as response:
                data = await response.json()

        settings["estimated_player_count"] = data["estimated_online_player_count"]

        # minimum_waiting_time = time after which match starts (except if the game is full) for the first player to join a room
        # extra_waiting_time_when_new_player_found = adds x seconds to minimum_waiting_time when a new player joins
        # accept_level_range = the range of levels (both up and down compared to your level) the opponents may have
        if settings["estimated_player_count"] < 20:
            settings["minimum_waiting_time"] = 20
            settings["extra_waiting_time_when_new_player_found"] = 15
            settings["accept_level_range"] = 100  # accept anything
        elif settings["estimated_player_count"] < 50:
            settings["minimum_waiting_time"] = 15
            settings["extra_waiting_time_when_new_player_found"] = 10
            settings["accept_level_range"] = 60
        elif settings["estimated_player_count"] < 100:
            settings["minimum_waiting_time"] = 10
            settings["extra_waiting_time_when_new_player_found"] = 10
            settings["accept_level_range"] = 30
        else:
            settings["minimum_waiting_time"] = 5
            settings["extra_waiting_time_when_new_player_found"] = 5
            settings["accept_level_range"] = 15

    # Start matchmaking
    for player in waiting_players:
        level = player.player["level"]
        if player.waiting_room == None:
            # Check if waiting room to join already exists
            waiting_room_found = False
            for waiting_room in waiting_rooms:
                if waiting_room_found:
                    break
                for room_player in waiting_room.players:
                    if room_player.player["level"] >= level - settings["accept_level_range"] or\
                       room_player.player["level"] <= level + settings["accept_level_range"]:
                        waiting_room_found = True
                        waiting_room.players.append(player)
                        waiting_room.writers.append(player.writer)
                        waiting_room.extra_waiting_time += settings["extra_waiting_time_when_new_player_found"]
                        player.waiting_room = waiting_room
                        break

            if not waiting_room_found:
                # Create new waiting room
                player.waiting_room = WaitingRoom(player.writer, player)
                waiting_rooms.append(player.waiting_room)

    # Loop all waiting rooms to check which ones are full or should be started because of the time limit
    for waiting_room in waiting_rooms:
        for writer in waiting_room.writers:
            if writer.is_closing():
                await waiting_room.disconnectPlayer(writer)

        if len(waiting_room.players) == 4:
            await waiting_room.start_game()
            continue

        start_time = waiting_room.first_player.waiting_start_time + \
            settings["minimum_waiting_time"] + waiting_room.extra_waiting_time
        print(start_time - current_time)
        if current_time >= start_time and len(waiting_room.players) > 1:
            await waiting_room.start_game()
            continue
