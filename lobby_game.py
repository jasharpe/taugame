from state import save_game, get_ranks
import time
from tornado.escape import xhtml_escape

TAU_PROPERTIES = ["colour", "number", "shading", "shape"]

class LobbyGame(object):

  def __init__(self, id, game, lobby, training, classic_cards, colour_blind):
    self.id = id
    self.game = game
    self.lobby = lobby
    self.training = training
    self.classic_cards = classic_cards
    self.colour_blind = colour_blind

    self.sockets = []
    self.messages = []
    self.hidden = False
    self.activity()

  def set_training_option(self, option, value):
    if not self.training:
      return

    updated = False
    if self.game.type == "n3tau" and option == "property":
      if value == "all":
        self.game.wrong_property_preference = None
        updated = True
      elif value in TAU_PROPERTIES:
        self.game.wrong_property_preference = TAU_PROPERTIES.index(value)
        updated = True

    if updated:
      self.send_training_options_to_all()

  def send_training_options_to_all(self):
    training_options = self.get_training_options()
    for socket in self.sockets:
      socket.send_training_options(training_options)

  def get_training_options(self):
    prop = self.game.wrong_property_preference
    return {
        'property' : None if prop is None else TAU_PROPERTIES[prop]
    }

  def activity(self):
    self.last_activity = time.time()

  def submit_tau(self, socket, cards):
    if self.game.started and not self.game.ended and not self.game.paused:
      result = self.game.submit_client_tau(map(tuple, cards), socket.name)

      if result.status == result.SUCCESS:
        if self.game.ended:
          self.lobby.send_game_list_update_to_all()
          (db_game, score) = save_game(self.game, self.training)
          self.game.player_ranks = get_ranks(score.elapsed_time, db_game.game_type, self.game.scores.keys(), score.num_players)
        self.send_update_to_all()
      elif result.status == result.OLD_FOUND_PUZZLE:
        socket.send_old_found_puzzle_tau_index(result.index)

  def start_game(self):
    if not self.game.started:
      self.game.start()
      self.lobby.send_game_list_update_to_all()
      self.send_update_to_all()

  def pause(self, pause):
    if self.game.is_pausable():
      if pause == "pause" and not self.game.paused and self.get_number_unique_players() < 2:
        self.game.pause()
        self.send_update_to_all()
      elif pause != "pause" and self.game.paused:
        self.game.unpause()
        self.send_update_to_all()

  def request_update(self, socket):
    if self.game.started:
      self.send_update(socket)

  def get_number_unique_players(self):
    names = set()
    for socket in self.sockets:
      names.add(socket.name)
    return len(names)

  def open_game_socket(self, socket):
    self.activity()
    self.add_chat(socket.name, socket.name + " has joined", "status")
    
    self.sockets.append(socket)
    self.lobby.socket_to_game[socket] = self
    self.send_scores_update_to_all()
    self.maybe_unhide_game()
    self.lobby.send_game_list_update_to_all()
    socket.send_history_update(self.messages)

  def close_game_socket(self, socket):
    name = socket.name
    self.activity()

    self.sockets.remove(socket)
    if socket in self.lobby.socket_to_game:
      del self.lobby.socket_to_game[socket]
    self.add_chat(name, name + " has left", "status")
    self.send_scores_update_to_all()
    self.maybe_hide_game()
    self.lobby.send_game_list_update_to_all()
    
    if not self.get_number_unique_players():
      self.pause("pause")

  def add_chat(self, name, message, message_type):
    self.messages.append((name, message, message_type))
    self.send_message_update_to_all(name, message, message_type)

  def send_update(self, socket):
    time = self.game.total_time if self.game.ended else self.game.get_total_time()

    numbers_map = None
    if self.game.ended:
      numbers_map = {}
      last_time = 0
      for (tau_time, number, player, cards) in self.game.taus:
        time_to_find = tau_time - last_time
        last_time = tau_time
        if not number in numbers_map:
          numbers_map[number] = []
        numbers_map[number].append(time_to_find)
      for (number, times) in numbers_map.items():
        numbers_map[number] = "avg %.02f %s" % (sum(times) / float(len(times)), str(map(lambda x: "%.02f" % x, times)))

    player_rank_info = None
    if self.game.ended and socket.name in self.game.player_ranks['players']:
      player_rank_info = self.game.player_ranks['players'][socket.name]
    elif self.game.ended:
      player_rank_info = self.game.player_ranks['global']

    (all_taus, all_stale_taus) = self.game.get_all_client_taus()

    is_pausable = self.game.is_pausable() and self.get_number_unique_players() < 2

    socket.send_update(self.game.get_client_board(), all_taus, all_stale_taus, self.game.paused, self.game.get_client_target_tau(), self.game.wrong_property, self.get_scores(), numbers_map, self.game.count_taus(), time, self.game.get_client_hint(), self.game.ended, player_rank_info, self.game.get_client_found_puzzle_taus(), self.get_training_options(), is_pausable)

  def send_update_to_all(self):
    for socket in self.sockets:
      self.send_update(socket)
  
  def send_message_update_to_all(self, name, message, message_type):
    for socket in self.sockets:
      socket.send_message_update(name, message, message_type)

  def send_scores_update_to_all(self):
    scores = self.get_scores()
    ended = self.game.ended
    is_pausable = self.game.is_pausable() and self.get_number_unique_players() < 2
    for socket in self.sockets:
      socket.send_scores_update(scores, ended, is_pausable)

  def get_scores(self):
    scores = {}
    for socket in self.sockets:
      name = socket.name
      if name in self.game.scores:
        scores[xhtml_escape(name)] = self.game.scores[name]
      else:
        scores[xhtml_escape(name)] = []
    for (name, score) in self.game.scores.items():
      if not xhtml_escape(name) in scores:
        scores[xhtml_escape(name) + " (ABSENT)"] = score
    return scores

  def cleanup(self, game_expiry):
    if self.sockets:
      return False
    if not self.game.ended and not self.hidden:
      if time.time() - self.last_activity > game_expiry:
        self.hidden = True
        return True
    return False

  def maybe_hide_game(self):
    if not self.game.started and not self.sockets:
      self.hidden = True
      self.lobby.send_game_list_update_to_all()

  def maybe_unhide_game(self):
    if self.hidden:
      self.hidden = False
      self.lobby.send_game_list_update_to_all()
