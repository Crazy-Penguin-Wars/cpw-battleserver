import aiohttp
import gameManager
import privateGameManager
import findGameManager

async def handle_ConnectMessage_MatchMaker(reader, writer, message):
    if message["game_type"] == 1: # Normal game
        # Request player data from main server
        url = "http://127.0.0.1:5055/get-player-data"
        params = {"id": message["id"]}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
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
                    "id": "sgid_04010210b1e184bc",
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
            "owner": "sgid_04010210b1e184bc"
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
        await waiting_room.join(writer, {
                    "id": "sgid_2",
                    "name": "Test",
                    "level": 10,
                    "clothes": [],
                    "worn_items": []
                }
        )


async def handle_ConnectMessage_BattleServer(reader, writer, message):
    writer.userId = message["id"]
    for game in gameManager.active_games:
        for player in game.players:
            if player["id"] == message["id"]:
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