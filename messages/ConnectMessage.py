import gameManager
import privateGameManager

async def handle_ConnectMessage_MatchMaker(reader, writer, message):
    if message["game_type"] == 1: # Normal game
        return {
            "t" : 27,
            "id": message["id"],
            "address": "127.0.0.1",
            "port": 5050,
            "map": "test_level",
            "battle_time": 300,
            "turn_time": 20,
            "seed": 10,
            "practice_mode": False,
            "players": [
                {
                    "id": "sgid_04010210b1e184bc",
                    "name": "Michielvde",
                    "level": 98
                },
                {
                    "id": "sgid_2",
                    "name": "Test",
                    "level": 98
                }
            ]
        }
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

        writer.waiting_room = privateGameManager.WaitingRoom(writer, player, game_name)
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
    game_already_created = False
    writer.userId = message["id"]
    for game in gameManager.active_games:
        for player in game.players:
            if player["id"] == message["id"]:
                print("Joining created game")
                game_already_created = True
                writer.game = game
                game.writers.append(writer)
                break
    if not game_already_created:
        print("Creating game")
        writer.game = gameManager.Game(reader, writer, [
            {
                "id": "sgid_04010210b1e184bc",
                "name": "Michielvde",
                "level": 98
            },
            {
                "id": "sgid_2",
                "name": "Test",
                "level": 98
            }
        ])
        gameManager.active_games.append(writer.game)
    return {
    "t" : 21,
    "id": message["id"],
    "map": "test_level",
    "battle_time": 300,
    "turn_time": 20,
    "seed": 10,
    "practice_mode": False,
    "players": [
        {
            "id": "sgid_04010210b1e184bc",
            "name": "Michielvde",
            "level": 98
        },
        {
            "id": "sgid_2",
            "name": "Test",
            "level": 98
        }
    ]
}