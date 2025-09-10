import aiohttp
import json
import os
from dotenv import load_dotenv
import socketUtils
import time
import base64

load_dotenv()

active_games = []

class Game:

    def __init__(self, players, match_time, turn_time, seed):
        self.writers = []

        self.players = players
        self.playersActive = players
        self.playerOrder = []
        self.currentPlayerTurn = 0
        self.disconnectingQueue = []
        self.respawnQueue = []
        self.resumeQueue = []
        self.amountRealPlayers = 0
        self.amountRealPlayersActive = 0
        self.amountAllPlayers = len(players)
        self.amountAllPlayersActive = self.amountAllPlayers
        self.playersReady = 0
        self.gameStarted = False
        self.turnStarted = False
        self.rewards = {}
        for player in players:
            player["ready"] = False
            if "FakePlayer" not in player["id"]:
                 self.amountRealPlayers += 1
                 self.amountRealPlayersActive += 1
            self.playerOrder.append(player["id"])
            self.rewards[player["id"]] = {
                "coins": 0,
                "cash": 0,
                "experience": 0,
                "score": 0,
                "usedItems": {},
                "earnedItems": {}
            }

        #random.shuffle(self.playerOrder)
        print(self.playerOrder)

        self.seed = seed
        self.turnTime = turn_time
        self.matchTime = match_time
        self.turnTimeLeft = self.turnTime * 1000
        self.matchTimeLeft = self.matchTime * 1000
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
                self.turnTimeLeft = self.turnTime * 1000
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

    def addPlayerToRespawnQueue(self, player):
        self.respawnQueue.append(player)
        self.resumeQueue.append(player)

    def add_reward(self, id, type, value):
        if "FakePlayer" in id:
            return
        match type:
            case "coins" | "cash" | "experience" | "score":
                self.rewards[id][type] = value # Do not add, the game sends the total amount
            case "usedItems" | "earnedItems":
                key = list(value.keys())[0]
                if key not in self.rewards[id][type]:
                    self.rewards[id][type][key] = 0
                self.rewards[id][type][key] += value[key]
            # don't care about the other cases

    def sort_players(self):
        # Sort by score first, then by coins, then by experience, then sort the IDs alphabetically
        return [k for k, v in sorted(self.rewards.items(), key=lambda x: (-x[1]['score'], -x[1]['coins'], -x[1]['experience'], x[0]))]


    def add_position_bonus_reward(self, id, players_sorted):
        print(f"ID: {id}")
        print(f"PLAYERS SORTED: {players_sorted}")
        # Values from config:
        rank_multipliers = [1, 1, 1, 1]
        exp_modifier = 1
        coins_modifier = 1

        rank = players_sorted.index(id) + 1 + (4 - self.amountRealPlayersActive)
        print(f"RANK: {rank}")

        multiplier = rank_multipliers[rank - 1]

        def calculate_bonus(modifier):
            print(f"NOT ROUNDED: {((self.rewards[id]["score"] - self.rewards[players_sorted[-1]]["score"]) * 0.25 + modifier) * multiplier}")
            return int(((self.rewards[id]["score"] - self.rewards[players_sorted[-1]]["score"]) * 0.25 + modifier) * multiplier)
        
        print(f"COIN BONUS: {calculate_bonus(coins_modifier)}")
        print(f"XP BONUS: {calculate_bonus(exp_modifier)}")
        self.rewards[id]["coins"] += calculate_bonus(coins_modifier)
        self.rewards[id]["experience"] += calculate_bonus(exp_modifier)
        print(f"COIN TOTAL: {self.rewards[id]["coins"]}")
        print(f"XP TOTAL: {self.rewards[id]["experience"]}")

    async def send_rewards_to_main_server(self):
        rewards_string = json.dumps(self.rewards)
        rewards_base64 = base64.urlsafe_b64encode(rewards_string.encode("utf-8")).decode("utf-8")
        url = "http://127.0.0.1:5055/update-rewards"
        params = {
            "rewards": rewards_base64,
            "connectionKey": os.environ["CONNECTION_KEY"]
        }
        async with aiohttp.ClientSession() as session:
            await session.post(url, params=params)

async def update():
     for game in active_games:
        response = {"t": 1}

        # Check for inactive players
        if game.gameStarted:
            for writer in game.writers:
                if writer.is_closing():
                    await game.disconnectPlayer(writer)
        

        # Check disconnectionQueue
        if len(game.disconnectingQueue) != 0 and game.playersReady == game.amountRealPlayersActive:
            for disconnecting_player in game.disconnectingQueue:
                # Send RemovePlayer
                disconnectMessage = {"t": 22, "removed_client": disconnecting_player, "reason": "disconnected"}
                await socketUtils.send_message_to_multiple_writers(disconnectMessage, game.writers) 
                # Reasons:
                # unexpected_message, disconnected, sync_error, time_out
                game.disconnectingQueue.remove(disconnecting_player)


        current_time = time.time() * 1000
        time_diff = current_time - game.lastWorldUpdate
        game.lastWorldUpdate = current_time

        # Check respawnQueue
        for respawning_player in game.respawnQueue:
            if respawning_player["respawn_time"] < current_time:
                if "respawn" not in response:
                    response["respawn"] = []
                response["respawn"].append(respawning_player)
                game.respawnQueue.remove(respawning_player)

        for resuming_player in game.resumeQueue:
            if resuming_player["resume_time"] < current_time:
                if "resume" not in response:
                    response["resume"] = []
                response["resume"].append(resuming_player)
                game.resumeQueue.remove(resuming_player)

        if game.gameStarted and game.turnTimeLeft > 0:

            game.turnTimeLeft = round(game.turnTimeLeft - time_diff)
            game.matchTimeLeft = round(game.matchTimeLeft - time_diff)

            response["ttl"] = game.turnTimeLeft
            response["mtl"] = game.matchTimeLeft

            if game.matchTimeLeft <= 0:
                game.gameStarted = False
                # Send MatchEnd message
                MatchEndMessage = {"t": 19}
                await socketUtils.send_message_to_multiple_writers(MatchEndMessage, game.writers)
                # Add position bonus rewards
                sorted_players = game.sort_players()
                for player in game.players:
                    if "FakePlayer" not in player["id"]:
                        game.add_position_bonus_reward(player["id"], sorted_players)
                # Send rewards to the main server (where they'll be added to the database)
                await game.send_rewards_to_main_server()
                return

            elif game.turnTimeLeft <= 0:
                print("[Debug] Start new turn")
                # Set all players as not ready
                for player in game.players:
                    player["ready"] = False
                game.playersReady = 0

                game.turnStarted = False

                # Send end turn message
                EndTurnMessage = {"t": 16, "id": game.playerOrder[game.currentPlayerTurn]}
                await socketUtils.send_message_to_multiple_writers(EndTurnMessage, game.writers)
                game.currentPlayerTurn = (game.currentPlayerTurn + 1) % game.amountAllPlayersActive

        if game.gameStarted:
            await socketUtils.send_message_to_multiple_writers(response, game.writers)