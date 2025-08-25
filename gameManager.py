import random
import socketUtils
import time

active_games = []

class Game:

    def __init__(self, reader, writer, players):
        self.reader = reader
        self.writers = []
        self.writers.append(writer)

        self.players = players
        self.playersActive = players
        self.playerOrder = []
        self.currentPlayerTurn = 0
        self.disconnectingQueue = []
        self.amountRealPlayers = 0
        self.amountRealPlayersActive = 0
        self.amountAllPlayers = len(players)
        self.amountAllPlayersActive = self.amountAllPlayers
        self.playersReady = 0
        self.gameStarted = False
        self.turnStarted = False
        for player in players:
            player["ready"] = False
            if "FakePlayer" not in player["id"]:
                 self.amountRealPlayers += 1
                 self.amountRealPlayersActive += 1
            self.playerOrder.append(player["id"])

        #random.shuffle(self.playerOrder)
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
        
        if self.playersReady == self.amountRealPlayersActive:
                print("All players ready")

                # All players ready, send start turn response
                response = {"t": 17, "id": self.playerOrder[self.currentPlayerTurn]}
                await socketUtils.send_message_to_multiple_writers(response, self.writers)

                self.gameStarted = True
                self.turnTimeLeft = 20000
                self.turnStarted = True

    async def disconnectPlayer(self, writer):
        userId = writer.userId

        already_left = True
        for player in self.playersActive:
             if player["id"] == userId:
                 already_left = False
                 break
        
        if already_left:
            return

        print("Disconnecting player " + userId)

        if self.amountRealPlayersActive == 1:
            # All players left, end game
            print("Destroy game")
            active_games.remove(self)
            return

        # Start next turn if needed
        next_turn_needed = False
        if self.playerOrder[self.currentPlayerTurn] == userId:
            self.currentPlayerTurn = (self.currentPlayerTurn + 1) % self.amountAllPlayersActive
            next_turn_needed = True

        # Remove player from active players
        self.amountRealPlayersActive -= 1
        self.amountAllPlayersActive -= 1
        current_turn_id = self.playerOrder[self.currentPlayerTurn]
        self.playerOrder.remove(userId)
        # Be sure that the currently active player didn't change
        self.currentPlayerTurn = self.playerOrder.index(current_turn_id)
        for player in self.playersActive:
            if player["id"] == userId:
                del player
                break

        # Remove player from writers
        self.writers.remove(writer)
        
        # Send end turn first
        if next_turn_needed:
            self.disconnectingQueue.append(userId)
            # Set all players as not ready
            for player in self.players:
                player["ready"] = False
            self.playersReady = 0

            self.turnStarted = False
            response = {"t": 16, "id": userId}
            await socketUtils.send_message_to_multiple_writers(response, self.writers)
        else:
            # Do not use queue and remove player immediately
            response = {"t": 22, "removed_client": userId, "reason": "disconnected"}
            await socketUtils.send_message_to_multiple_writers(response, self.writers) 

async def update():
     #print("Active games: " + str(len(active_games)))
     for game in active_games:
        # Check for inactive players
        if game.gameStarted:
            for writer in game.writers:
                #print(len(game.writers))
                if writer.is_closing():
                    await game.disconnectPlayer(writer)
        

        # Check disconnectionQueue
        if len(game.disconnectingQueue) != 0 and game.playersReady == game.amountRealPlayersActive:
            for disconnecting_player in game.disconnectingQueue:
                # Send RemovePlayer
                response = {"t": 22, "removed_client": disconnecting_player, "reason": "disconnected"}
                await socketUtils.send_message_to_multiple_writers(response, game.writers) 
                # Reasons:
                # unexpected_message, disconnected, sync_error, time_out
                game.disconnectingQueue.remove(disconnecting_player)


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

            if game.matchTimeLeft <= 0:
                response = {"t": 19}

            elif game.turnTimeLeft <= 0:
                print("[Debug] Start new turn")
                # Set all players as not ready
                for player in game.players:
                    player["ready"] = False
                game.playersReady = 0

                game.turnStarted = False

                # Send end turn message
                response = {"t": 16, "id": game.playerOrder[game.currentPlayerTurn]}
                game.currentPlayerTurn = (game.currentPlayerTurn + 1) % game.amountAllPlayersActive

            await socketUtils.send_message_to_multiple_writers(response, game.writers)