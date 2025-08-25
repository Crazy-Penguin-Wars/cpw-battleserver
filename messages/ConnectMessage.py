import gameManager

async def handle_ConnectMessage_MatchMaker(reader, writer, message):
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