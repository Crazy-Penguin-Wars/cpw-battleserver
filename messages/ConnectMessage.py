import os
import aiohttp
import gameManager
import privateGameManager
import findGameManager
from config import HTTP_TIMEOUT_SECONDS, MAIN_SERVER_URL

def is_valid_player_id(value):
    return isinstance(value, str) and 0 < len(value) <= 128

async def handle_ConnectMessage_MatchMaker(reader, writer, message):
    if not is_valid_player_id(message.get("id")):
        return {"t": 31, "id": message.get("id", ""), "successful": False}
    if message["game_type"] == 1: # Normal game
        # Request player data from main server
        url = f"{MAIN_SERVER_URL}/get-player-data"
        params = {"id": message["id"]}

        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                player = await response.json()

        findGameManager.add_new_player_to_matchmaking(player, writer)
        writer.userId = message["id"]
    elif message["game_type"] == 2 and message["owner"]: # Private game, host
        game_name = message["game_name"]
        extra_number = 1
        while privateGameManager.is_game_existing(game_name):
            game_name = game_name + str(extra_number)
            extra_number += 1

        player = {
                    "id": message["id"],
                    "name": "Michielvde",
                    "level": 10,
                    "clothes": [],
                    "worn_items": []
                }

        writer.waiting_room = privateGameManager.PrivateWaitingRoom(writer, player, game_name)
        writer.userId = message["id"]
        privateGameManager.waiting_rooms.append(writer.waiting_room)

        return {
            "t" : 31,
            "id": message["id"],
            "successful": True,
            "players": [player],
            "owner": writer.userId
        }
    
    elif message["game_type"] == 2 and not message["owner"]: # Private game, join
        game_name = message["game_name"]
        waiting_room = privateGameManager.get_waiting_room(game_name)
        if waiting_room == -1:
            return {
                "t" : 31,
                "id": message["id"],
                "successful": False
            }
        writer.waiting_room = waiting_room
        writer.userId = message["id"]
        joined = await waiting_room.join(writer, {
                    "id": writer.userId,
                    "name": "Test",
                    "level": 10,
                    "clothes": [],
                    "worn_items": []
                }
        )
        if not joined:
            return {"t": 31, "id": writer.userId, "successful": False}
        return {"t": 31, "id": writer.userId, "successful": True}


async def handle_ConnectMessage_BattleServer(reader, writer, message):
    if not is_valid_player_id(message.get("id")):
        return None
    writer.userId = message["id"]
    for game in gameManager.active_games:
        for player in game.players:
            if player["id"] == message["id"]:
                if any(getattr(existing_writer, "userId", None) == writer.userId for existing_writer in game.writers):
                    return None
                print("Joining created game")
                writer.game = game
                game.writers.append(writer)
                return {
                    "t" : 21,
                    "id": message["id"],
                    "map": "test_level",
                    "battle_time": game.matchTime,
                    "turn_time": game.turnTime,
                    "seed": game.seed,
                    "practice_mode": False,
                    "players": game.players
                }
