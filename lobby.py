from game import Game
from state import save_game, get_ranks
import time

class InvalidGameId(Exception):
  pass

class Lobby(object):
  def __init__(self):
    self.sockets = []
    self.games = {}
    self.hidden_games = set()
    self.last_activity = {}
    self.socket_to_game = {}
    self.game_to_sockets = {}
    self.game_to_messages = {}

    self.game_list_sockets = []

  def new_game(self, type, name, parent, quick):
    if len(self.games.keys()) == 0:
      next_id = 0
    else:
      next_id = max(self.games.keys()) + 1

    self.games[next_id] = Game(type, quick)

    if parent is not None and parent in self.games:
      parent_game = self.games[parent]
      self.add_chat(parent, name, (type, next_id), "new_game")
    self.game_to_sockets[next_id] = []
    self.game_to_messages[next_id] = []
    self.send_game_list_update_to_all()
    return next_id

  def is_valid_game(self, game_id):
    return game_id in self.games

  def get_game(self, game_id):
    if not self.is_valid_game(game_id):
      raise InvalidGameId()
    return self.games[game_id]

  def transform_games(self, games):
    return [{
      'id' : game_id,
      'size' : game.size,
      'type' : game.type,
      'players' : self.get_players_in_game(game_id),
    } for (game_id, game) in games]

  def maybe_hide_game(self, game_id):
    game = self.games[game_id]
    sockets = self.game_to_sockets[game_id]
    if not game.started and not sockets:
      self.hidden_games.add(game_id)
      self.send_game_list_update_to_all()

  def maybe_unhide_game(self, game_id):
    if game_id in self.hidden_games:
      self.hidden_games.remove(game_id)
      self.send_game_list_update_to_all()

  def activity(self, game_id):
    self.last_activity[game_id] = time.time()

  def cleanup_games(self):
    updated = False
    for (game_id, game) in self.games.items():
      sockets = self.game_to_sockets[game_id]
      if sockets:
        continue
      if game.started and not game.ended and not game_id in self.hidden_games:
        if time.time() - self.last_activity[game_id] > GAME_EXPIRY:
          self.hidden_games.add(game_id)
          updated = True
    if updated:
      self.send_game_list_update_to_all()

  def get_games(self, see_more_ended):
    sorted_game_items = filter(lambda x: not x[0] in self.hidden_games, sorted(self.games.items(), None, lambda game: game[0]))
    new_games = filter(lambda g: not g[1].started, sorted_game_items)
    started_games = filter(lambda g: g[1].started and not g[1].ended, sorted_game_items)
    if see_more_ended:
      ended_games = filter(lambda g: g[1].ended, sorted_game_items)
    else:
      ended_games = filter(lambda g: g[1].ended, sorted_game_items)[-5:]
    return (self.transform_games(new_games),
        self.transform_games(started_games),
        self.transform_games(ended_games))

  def send_game_list_update_to_all(self):
    for socket in self.game_list_sockets:
      (new_games, started_games, ended_games) = self.get_games(socket.see_more_ended)
      socket.send_game_list_update(*self.get_games(socket.see_more_ended))

  def get_scores(self, game_id):
    game = self.games[game_id]
    
    scores = {}
    for socket in self.game_to_sockets[game_id]:
      name = socket.name
      if name in game.scores.keys():
        scores[name] = game.scores[name]
      else:
        scores[name] = []
    for (name, score) in game.scores.items():
      if not name in scores.keys():
        scores[name + " (ABSENT)"] = score
    return scores

  def send_scores_update_to_all(self, game_id):
    scores = self.get_scores(game_id)
    ended = self.games[game_id].ended
    for socket in self.game_to_sockets[game_id]:
      socket.send_scores_update(scores, ended)

  def send_message_update_to_all(self, game_id, name, message, message_type):
    for socket in self.game_to_sockets[game_id]:
      socket.send_message_update(name, message, message_type)

  def send_update_to_all(self, game_id):
    for socket in self.game_to_sockets[game_id]:
      self.send_update(socket)

  def send_update(self, socket):
    game_id = socket.game_id
    game = self.games[game_id]
    time = game.total_time if game.ended else game.get_total_time()

    numbers_map = None
    if game.ended:
      numbers_map = {}
      last_time = 0
      for (tau_time, number, player, cards) in game.taus:
        time_to_find = tau_time - last_time
        last_time = tau_time
        if not number in numbers_map:
          numbers_map[number] = []
        numbers_map[number].append(time_to_find)
      for (number, times) in numbers_map.items():
        numbers_map[number] = "avg %.02f %s" % (sum(times) / float(len(times)), str(map(lambda x: "%.02f" % x, times)))

    player_rank_info = None
    if game.ended and socket.name in game.player_ranks['players']:
      player_rank_info = game.player_ranks['players'][socket.name]
    elif game.ended:
      player_rank_info = game.player_ranks['global']

    socket.send_update(game.get_client_board(), game.get_all_client_taus(), game.paused, game.get_client_target_tau(), game.wrong_property, self.get_scores(game_id), numbers_map, game.count_taus(), time, game.get_client_hint(), game.ended, player_rank_info, game.get_client_found_puzzle_taus())

  def get_players_in_lobby(self):
    players = []
    for socket in self.game_list_sockets:
      try:
        players.append(socket.name)
      except:
        pass
    return sorted(players)

  def send_lobby_player_list_update_to_all(self):
    players = self.get_players_in_lobby()
    for socket in self.game_list_sockets:
      socket.send_player_list_update(players)

  def add_chat(self, game_id, name, message, message_type):
    self.game_to_messages[game_id].append((name, message, message_type))
    self.send_message_update_to_all(game_id, name, message, message_type)

  def submit_tau(self, socket, name, cards):
    game = self.socket_to_game[socket]
    if game.started and not game.ended and not game.paused:
      result = game.submit_client_tau(map(tuple, cards), name)

      if result.status == result.SUCCESS:
        if game.ended:
          self.send_game_list_update_to_all()
          (db_game, score) = save_game(game)
          game.player_ranks = get_ranks(score.elapsed_time, db_game.game_type, game.scores.keys(), score.num_players)
        self.send_update_to_all(socket.game_id)
      elif result.status == result.OLD_FOUND_PUZZLE:
        socket.send_old_found_puzzle_tau_index(result.index)

  def get_players_in_game(self, game_id):
    players = set()
    for socket in self.game_to_sockets[game_id]:
      try:
        players.add(socket.name)
      except:
        pass
    return sorted(players)

  def update_game_list_socket(self, socket, see_more_ended):
    socket.send_player_list_update(self.get_players_in_lobby())
    socket.send_game_list_update(*self.get_games(see_more_ended))

  def open_game_list_socket(self, socket):
    self.game_list_sockets.append(socket)
    self.send_lobby_player_list_update_to_all()

  def close_game_list_socket(self, socket):
    self.game_list_sockets.remove(socket)
    self.send_lobby_player_list_update_to_all()

  def open_game_socket(self, socket):
    game_id = socket.game_id
    self.activity(game_id)
    self.add_chat(game_id, socket.name, socket.name + " has joined", "status")
    
    self.sockets.append(socket)
    self.socket_to_game[socket] = self.games[game_id]
    self.game_to_sockets[game_id].append(socket)
    self.send_scores_update_to_all(game_id)
    self.maybe_unhide_game(game_id)
    self.send_game_list_update_to_all()
    socket.send_history_update(self.get_all_messages(game_id))

  def close_game_socket(self, socket):
    game_id = socket.game_id
    name = socket.name
    self.activity(socket.game_id)
    game = self.socket_to_game[socket]
    
    paused = False
    if len(self.game_to_sockets[game_id]) < 2:
      paused = self.pause(game_id, "pause", delay_update=True)
    self.sockets.remove(socket)
    if socket in self.socket_to_game.keys():
      del self.socket_to_game[socket]
    if socket in self.game_to_sockets[game_id]:
      self.game_to_sockets[game_id].remove(socket)
    self.add_chat(game_id, name, name + " has left", "status")
    self.send_scores_update_to_all(game_id)
    self.maybe_hide_game(game_id)
    self.send_game_list_update_to_all()
    if paused:
      self.send_update_to_all(game_id)

  def request_update(self, socket):
    if self.socket_to_game[socket].started:
      self.send_update(socket)

  def start_game(self, game_id):
    game = self.games[game_id]
    if not game.started:
      game.start()
      self.send_game_list_update_to_all()
      self.send_update_to_all(game_id)

  def pause(self, game_id, pause, delay_update=False):
    game = self.games[game_id]
    if game.is_pausable():
      if pause == "pause" and not game.paused and len(self.game_to_sockets[game_id]) < 2:
        game.pause()
        if not delay_update:
          self.send_update_to_all(game_id)
        return True
      elif pause != "pause" and game.paused:
        game.unpause()
        if not delay_update:
          self.send_update_to_all(game_id)
        return True
    return False

  def get_all_messages(self, game_id):
    return self.game_to_messages[game_id]
