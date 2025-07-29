import random
import socketUtils
import time

active_games = []

class Game:
    writers = []

    def __init__(self, reader, writer, players):
        self.reader = reader
        self.writers.append(writer)

        self.players = players
        self.playerOrder = []
        self.currentPlayerTurn = 0
        self.amountRealPlayers = 0
        self.amountAllPlayers = len(players)
        self.playersReady = 0
        self.gameStarted = False
        self.turnStarted = False
        for player in players:
            player["ready"] = False
            if "FakePlayer" not in player["id"]:
                 self.amountRealPlayers += 1
            self.playerOrder.append(player["id"])

        random.shuffle(self.playerOrder)
        print(self.playerOrder)

        self.turnTimeLeft = 20000
        self.matchTimeLeft = 300000
        self.lastWorldUpdate = time.time() * 1000

    async def playerReady(self, player_id):
        print("Player ready")
        for player in self.players:
             if player["id"] == player_id:
                if not player["ready"]:
                    player["ready"] = True
                    self.playersReady += 1
                break
        
        if self.playersReady == self.amountRealPlayers:
                print("All players ready")

                # All players ready, send start turn response
                response = {"t": 17, "id": self.playerOrder[self.currentPlayerTurn]}
                await socketUtils.send_message_to_multiple_writers(response, self.writers)

                self.gameStarted = True
                self.turnTimeLeft = 20000
                self.turnStarted = True

async def update():
     for game in active_games:
        current_time = time.time() * 1000
        time_diff = current_time - game.lastWorldUpdate
        game.lastWorldUpdate = current_time
        if game.gameStarted and game.turnTimeLeft > 0:
            response = {"t": 1}

            game.turnTimeLeft = round(game.turnTimeLeft - time_diff)
            game.matchTimeLeft = round(game.matchTimeLeft - time_diff)

            response["ttl"] = game.turnTimeLeft
            response["mtl"] = game.matchTimeLeft
            response["id"] = "sgid_04010210b1e184bc"

            if game.turnTimeLeft <= 0:
                print("[Debug] Start new turn")
                # Set all players as not ready
                for player in game.players:
                    player["ready"] = False
                game.playersReady = 0

                game.turnStarted = False

                # Send start turn message
                response = {"t": 16, "id": game.playerOrder[game.currentPlayerTurn]}
                game.currentPlayerTurn = (game.currentPlayerTurn + 1) % game.amountAllPlayers

            await socketUtils.send_message_to_multiple_writers(response, game.writers)