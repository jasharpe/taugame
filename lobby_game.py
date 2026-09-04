from state import save_game, get_ranks
import time
from tornado.escape import xhtml_escape
from tornado.ioloop import IOLoop

TAU_PROPERTIES = ["colour", "number", "shading", "shape"]

class LobbyGame(object):

  def __init__(self, id, game, lobby, training, creator=None):
    self.id = id
    self.game = game
    self.lobby = lobby
    self.training = training
    # Whoever started the game can always pause it, even once other players
    # have joined.
    self.creator = creator

    self.sockets = []
    self.messages = []
    self.hidden = False
    # Pending call_later that clears taus once their take delay elapses.
    self.expiry_handle = None
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
      result = self.game.submit_client_tau(list(map(tuple, cards)), socket.name)

      if result.status == result.SUCCESS:
        self.finish_if_ended()
        self.schedule_pending_expiry()
        self.send_update_to_all()
      elif result.status == result.OLD_FOUND_PUZZLE:
        socket.send_old_found_puzzle_tau_index(result.index)

  # Saves the game the first time it is seen to have finished. With a take delay
  # the finish can happen when a tau expires rather than when it is submitted,
  # so this is called from both places.
  def finish_if_ended(self):
    if self.game.ended and self.game.score_id is None:
      self.lobby.send_game_list_update_to_all()
      (db_game, score, elapsed_time) = save_game(self.game, self.training)
      self.game.score_id = score.id
      self.game.player_ranks = get_ranks(elapsed_time, db_game.game_type, list(self.game.scores.keys()), score.num_players)

  # A tau taken with a take delay stays on the board, so something has to come
  # back later and clear it.
  def schedule_pending_expiry(self):
    if self.expiry_handle is not None:
      return
    delay = self.game.seconds_until_next_expiry()
    if delay is None:
      return
    self.expiry_handle = IOLoop.current().call_later(delay, self.on_pending_expiry)

  def on_pending_expiry(self):
    self.expiry_handle = None
    if self.game.expire_pending_taus():
      self.finish_if_ended()
      self.send_update_to_all()
    # More taus may still be counting down behind this one.
    self.schedule_pending_expiry()

  def start_game(self):
    if not self.game.started:
      self.game.start()
      self.lobby.send_game_list_update_to_all()
      self.send_update_to_all()

  def pause(self, socket, pause):
    if self.game.is_pausable():
      if pause == "pause" and not self.game.paused and self.can_pause(socket):
        self.game.pause()
        self.send_update_to_all()
      elif pause != "pause" and self.game.paused and self.can_unpause(socket):
        self.game.unpause()
        self.send_update_to_all()

  # Pausing is meant to be for solo games only. Sockets are pinged, so anyone
  # still listed really is here, whether or not they have taken a tau yet.
  def can_pause(self, socket):
    if socket.name == self.creator:
      return True
    return self.get_number_unique_players() < 2

  # The creator paused the game, so the creator decides when it resumes.
  # Otherwise a game they paused and walked away from would be stuck for
  # everyone else, so once they are gone anyone may start it again.
  def can_unpause(self, socket):
    if socket.name == self.creator:
      return True
    return not self.creator_present()

  def creator_present(self):
    return any([socket.name == self.creator for socket in self.sockets])

  # What the pause button does next for this player, which is what decides
  # whether it is offered to them at all.
  def can_use_pause_button(self, socket):
    if self.game.paused:
      return self.can_unpause(socket)
    return self.can_pause(socket)

  # Called when the last socket goes away, which no player is around to ask for.
  def pause_when_empty(self):
    if self.game.is_pausable() and not self.game.paused:
      self.game.pause()

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
      self.pause_when_empty()

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
      for (number, times) in list(numbers_map.items()):
        numbers_map[number] = "avg %.02f %s" % (sum(times) / float(len(times)), str(["%.02f" % x for x in times]))

    player_rank_info = None
    if self.game.ended and socket.name in self.game.player_ranks['players']:
      player_rank_info = self.game.player_ranks['players'][socket.name]
    elif self.game.ended:
      player_rank_info = self.game.player_ranks['global']

    (all_taus, all_stale_taus) = self.game.get_all_client_taus()

    is_pausable = self.game.is_pausable() and self.can_use_pause_button(socket)

    socket.send_update(self.game.get_client_board(), all_taus, all_stale_taus, self.game.paused, self.game.get_client_target_tau(), self.game.wrong_property, self.get_scores(), numbers_map, self.game.count_taus(), time, self.game.get_client_hint(), self.game.ended, player_rank_info, self.game.get_client_found_puzzle_taus(), self.get_training_options(), is_pausable, self.game.score_id, self.game.get_client_pending_taus())

  def send_update_to_all(self):
    for socket in self.sockets:
      self.send_update(socket)
  
  def send_message_update_to_all(self, name, message, message_type):
    for socket in self.sockets:
      socket.send_message_update(name, message, message_type)

  def send_scores_update_to_all(self):
    scores = self.get_scores()
    ended = self.game.ended
    for socket in self.sockets:
      # Per player, because the creator alone can pause and unpause at will.
      is_pausable = self.game.is_pausable() and self.can_use_pause_button(socket)
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
