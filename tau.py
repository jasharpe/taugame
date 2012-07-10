# -- coding: utf-8 --

import tornado.web
import tornado.auth
import tornado.websocket
import tornado.httpserver
from tornado.escape import url_escape, url_unescape
import json
import os
from game import Game, InvalidGameType
import argparse
import datetime, time
import ssl
from state import save_game, get_all_high_scores, get_ranks, get_graph_data, check_name, set_name, get_name
from secrets import cookie_secret

# The time in seconds that games should be allows to live without activity
# before they are eligible to be hidden if they contain no players.
GAME_EXPIRY = 1200

# The number of seconds between game cleanup sweeps.
GAME_CLEANUP_INTERVAL = 600

settings = {
    "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
    "static_path" : os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret" : cookie_secret,
}

# Tau sockets
sockets = []
games = {}
hidden_games = set()
last_activity = {}
socket_to_game = {}
game_to_sockets = {}
game_to_messages = {}

# game list sockets
game_list_sockets = []

def maybe_hide_game(game_id):
  game = games[game_id]
  sockets = game_to_sockets[game_id]
  if not game.started and not sockets:
    hidden_games.add(game_id)
    send_game_list_update_to_all()

def maybe_unhide_game(game_id):
  if game_id in hidden_games:
    hidden_games.remove(game_id)
    send_game_list_update_to_all()

def activity(game_id):
  last_activity[game_id] = time.time()

def cleanup_games():
  updated = False
  for (game_id, game) in games.items():
    sockets = game_to_sockets[game_id]
    if sockets:
      continue
    if game.started and not game.ended and not game_id in hidden_games:
      if time.time() - last_activity[game_id] > GAME_EXPIRY:
        hidden_games.add(game_id)
        updated = True
  if updated:
    send_game_list_update_to_all()

def get_games(see_more_ended):
  sorted_game_items = filter(lambda x: not x[0] in hidden_games, sorted(games.items(), None, lambda game: game[0]))
  new_games = filter(lambda g: not g[1].started, sorted_game_items)
  started_games = filter(lambda g: g[1].started and not g[1].ended, sorted_game_items)
  if see_more_ended:
    ended_games = filter(lambda g: g[1].ended, sorted_game_items)
  else:
    ended_games = filter(lambda g: g[1].ended, sorted_game_items)[-5:]
  return (new_games, started_games, ended_games)

def send_game_list_update_to_all():
  for socket in game_list_sockets:
    (new_games, started_games, ended_games) = get_games(socket.see_more_ended)
    socket.send_game_list_update(new_games, started_games, ended_games)

def get_players_in_game(game_id):
  players = set()
  for socket in game_to_sockets[game_id]:
    try:
      players.add(socket.name)
    except:
      pass
  return sorted(players)

class GameListWebSocketHandler(tornado.websocket.WebSocketHandler):
  def open(self, see_more_ended):
    self.see_more_ended = int(see_more_ended)
    self.name = url_unescape(self.get_secure_cookie("name"))
    game_list_sockets.append(self)
    self.send_player_list_update_to_all()
  
  def on_close(self):
    game_list_sockets.remove(self)
    self.send_player_list_update_to_all()

  def on_message(self, message_json):
    message = json.loads(message_json)
    if message['type'] == 'update':
      self.send_player_list_update(self.get_players())
      self.send_game_list_update(*get_games(self.see_more_ended))

  def send_player_list_update_to_all(self):
    players = self.get_players()
    for socket in game_list_sockets:
      socket.send_player_list_update(players)

  def send_player_list_update(self, players):
    self.write_message(json.dumps({
        'type' : 'players',
        'players' : players
    }))

  def get_players(self):
    players = []
    for socket in game_list_sockets:
      try:
        players.append(socket.name)
      except:
        pass
    return sorted(players)

  def transform_games(self, games):
    return [{
      'id' : game_id,
      'size' : game.size,
      'type' : game.type,
      'players' : get_players_in_game(game_id),
    } for (game_id, game) in games]

  def send_game_list_update(self, new_games, started_games, ended_games):
    self.write_message(json.dumps({
        'type' : 'games',
        'new_games' : self.transform_games(new_games),
        'started_games' : self.transform_games(started_games),
        'ended_games' : self.transform_games(ended_games)
    }))

class TauWebSocketHandler(tornado.websocket.WebSocketHandler):
  def open(self, game_id):
    self.game_id = int(game_id)
    activity(self.game_id)
    self.name = url_unescape(self.get_secure_cookie("name"))
    self.add_chat(self.name, self.name + " has joined", "status")
    if not self.game_id in games:
      raise ValueError("game_id %d is bad!" % self.game_id)
    sockets.append(self)
    socket_to_game[self] = games[self.game_id]
    game_to_sockets[self.game_id].append(self)
    self.send_scores_update_to_all()
    maybe_unhide_game(self.game_id)
    send_game_list_update_to_all()
    self.write_message(json.dumps({
        'type' : 'history',
        'messages' : game_to_messages[self.game_id]
    }))

  def on_close(self):
    activity(self.game_id)
    game = socket_to_game[self]
    
    paused = False
    if len(game_to_sockets[self.game_id]) < 2:
      paused = self.pause("pause")
    sockets.remove(self)
    if self in socket_to_game.keys():
      del socket_to_game[self]
    if self in game_to_sockets[self.game_id]:
      game_to_sockets[self.game_id].remove(self)
    self.add_chat(self.name, self.name + " has left", "status")
    self.send_scores_update_to_all()
    maybe_hide_game(self.game_id)
    send_game_list_update_to_all()
    if paused:
      self.send_update_to_all()

  def pause(self, pause):
    game = socket_to_game[self]
    if game.is_pausable():
      if pause == "pause" and not game.paused and len(game_to_sockets[self.game_id]) < 2:
        game.pause()
        return True
      elif pause != "pause" and game.paused:
        game.unpause()
        return True
    return False

  def get_scores(self):
    game = socket_to_game[self]
    
    scores = {}
    for socket in game_to_sockets[self.game_id]:
      name = socket.name
      if name in game.scores.keys():
        scores[name] = game.scores[name]
      else:
        scores[name] = []
    for (name, score) in game.scores.items():
      if not name in scores.keys():
        scores[name + " (ABSENT)"] = score
    return scores

  def send_scores_update_to_all(self):
    for socket in game_to_sockets[self.game_id]:
      socket.send_scores_update()

  def send_scores_update(self):
    game = socket_to_game[self]

    self.write_message(json.dumps({
        'type' : 'scores',
        'scores' : self.get_scores(),
        'ended' : game.ended
    }))

  def send_message_update_to_all(self, name, message, message_type):
    for socket in game_to_sockets[self.game_id]:
      socket.send_message_update(name, message, message_type)

  def send_message_update(self, name, message, message_type):
    self.write_message(json.dumps({
        'type' : 'chat',
        'name' : name,
        'message' : message,
        'message_type' : message_type,
    }))

  def send_update_to_all(self):
    for socket in game_to_sockets[self.game_id]:
      socket.send_update()

  def send_update(self):
    game = socket_to_game[self]
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
    if game.ended and self.name in game.player_ranks['players']:
      player_rank_info = game.player_ranks['players'][self.name]
    elif game.ended:
      player_rank_info = game.player_ranks['global']

    self.write_message(json.dumps({
        'type' : 'update',
        'board' : game.get_client_board(),
        'paused' : game.paused,
        'target' : game.get_client_target_tau(),
        'scores' : self.get_scores(),
        'avg_number' : numbers_map,
        'number' : game.count_taus(),
        'time' : time,
        'hint' : game.get_client_hint() if args.hints else None,
        'ended' : game.ended,
        'player_rank_info' : player_rank_info,
        # puzzle mode
        'found_puzzle_taus' : game.get_client_found_puzzle_taus(),
    }))

  def send_old_found_puzzle_tau_index(self, index):
    self.write_message(json.dumps({
        'type' : 'old_found_puzzle_tau',
        'index' : index,
    }))

  def add_chat(self, name, message, message_type):
    game_to_messages[self.game_id].append((name, message, message_type))
    self.send_message_update_to_all(name, message, message_type)

  def on_message(self, message_json):
    message = json.loads(message_json)
    if message['type'] == 'start':
      if not socket_to_game[self].started:
        socket_to_game[self].start()
      send_game_list_update_to_all()
      self.send_update_to_all()
    elif message['type'] == 'update':
      if socket_to_game[self].started:
        self.send_update()
    elif message['type'] == 'chat':
      self.add_chat(message['name'], message['message'], "chat")
    elif message['type'] == 'pause':
      if self.pause(message['pause']):
        self.send_update_to_all()
    elif message['type'] == 'submit':
      game = socket_to_game[self]
      if game.started and not game.ended and not game.paused:
        result = game.submit_client_tau(map(tuple, message['cards']), url_unescape(self.get_secure_cookie("name")))

        if result.status == result.SUCCESS:
          if game.ended:
            send_game_list_update_to_all()
            (db_game, score) = save_game(game)
            game.player_ranks = get_ranks(score.elapsed_time, db_game.game_type, game.scores.keys(), score.num_players)
          self.send_update_to_all()
        elif result.status == result.OLD_FOUND_PUZZLE:
          self.send_old_found_puzzle_tau_index(result.index)

def require_name(f):
  from functools import wraps
  @wraps(f)
  def wrapper(*args, **kwargs):
    self = args[0]
    # If user doesn't have a name, go to name chooser.
    if not self.get_secure_cookie("name"):
      self.redirect("/choose_name")
      return
    # If user has a reserved name, go to name chooser.
    name = url_unescape(self.get_secure_cookie("name"))
    user = get_user(self)
    email = None
    if user is not None:
      email = user['email']
    if not check_name(name, email):
      self.clear_cookie("name")
      self.redirect("/choose_name")
      return
    return f(*args, **kwargs)
  return wrapper

class MainHandler(tornado.web.RequestHandler):
  @require_name
  def get(self):
    self.render(
        "game_list.html",
        see_more_ended=int(self.get_argument('see_more_ended', default=False)),
        player=url_unescape(self.get_secure_cookie("name")))

class GraphHandler(tornado.web.RequestHandler):
  def get(self, player):
    try:
      time_offset = int(url_unescape(self.get_cookie("time_offset")))
    except:
      time_offset = 0
    self.render(
        "graph.html",
        player=player,
        graph_data=get_graph_data(player),
        time_offset=time_offset)

class LeaderboardHandler(tornado.web.RequestHandler):
  def get(self, leaderboard_type, leaderboard_object="", slash_separated_players=None, conjunction=None):
    if slash_separated_players:
      players = filter(None, slash_separated_players.split("/"))
    else:
      players = []
    unique_players = leaderboard_object == "players/"
    all_high_scores = get_all_high_scores(10, leaderboard_type, players, conjunction, unique_players=unique_players)
    try:
      time_offset = int(url_unescape(self.get_cookie("time_offset")))
    except:
      time_offset = 0
    self.render(
        "leaderboard.html",
        players=players,
        all_high_scores=all_high_scores,
        leaderboard_types=[('alltime', 'All Time'), ('thisweek', 'This Week'), ('today', 'Today')],
        selected_leaderboard_type=leaderboard_type,
        leaderboard_object=("players/" if unique_players else ""),
        time_offset=time_offset,
        conjunction=conjunction)

def get_user(request_handler):
  if request_handler.get_secure_cookie("google_user"):
    return json.loads(url_unescape(request_handler.get_secure_cookie("google_user")))
  return None

class ChooseNameHandler(tornado.web.RequestHandler):
  def get(self):
    user = get_user(self)
    name = None
    if user is not None:
      name = get_name(user['email'])
    self.render("choose_name.html", user=user, name=name)

  def post(self):
    name = self.get_argument("name")
    # validate name
    if "/" in name:
      # TODO: put in error code
      # TODO: escape names properly generally so we don't need to outlaw slashes
      self.redirect("/choose_name?slash_error=1")
      return

    user = get_user(self)
    email = None
    if user is not None:
      email = user['email']
    
    if not check_name(name, email):
      self.redirect("/choose_name?name_in_use_error=1")
      return
    if email is not None:
      set_name(email, name)
    self.set_secure_cookie("name", url_escape(name))
    self.redirect("/")

class NewGameHandler(tornado.web.RequestHandler):
  @require_name
  def post(self, type):
    if len(games.keys()) == 0:
      next_id = 0
    else:
      next_id = max(games.keys()) + 1

    try:
      games[next_id] = Game(type, args.quick)
    except InvalidGameType:
      print 'Invalid game type: ' + type
      self.redirect('/')
      return

    game_to_sockets[next_id] = []
    game_to_messages[next_id] = []
    send_game_list_update_to_all()
    self.redirect("/game/%d" % next_id)

class GameHandler(tornado.web.RequestHandler):
  game_type_to_type_string_map = {
    "3tau" : "3 Tau",
    "6tau" : "6 Tau",
    "g3tau" : "Generalized 3 Tau",
    "i3tau" : "Insane 3 Tau",
    "e3tau" : "Easy 3 Tau (beta)",
    "4tau" : "4 Tau",
    "3ptau" : "3 Projective Tau",
    "z3tau" : "Puzzle 3 Tau",
    "4otau" : "4 Outer Tau",
  }

  @require_name
  def get(self, game_id):
    if not int(game_id) in games:
      self.redirect("/?invalid_game_id_error=1")
      return
    game = games[int(game_id)]
    self.render(
        "game.html",
        game_id=game_id,
        user_name=url_unescape(self.get_secure_cookie("name")),
        game_type=self.game_type_to_type_string_map[game.type],
        game=game)

class TimeHandler(tornado.web.RequestHandler):
  def post(self):
    new_time_offset = url_escape(self.get_argument("time_offset"))
    self.set_cookie("time_offset", new_time_offset)

class AboutHandler(tornado.web.RequestHandler):
  def get(self):
    cards = {}
    shapes = ["circle", "square", "triangle"]
    shadings = ["empty", "shaded", "solid"]
    numbers = ["one", "two", "three"]
    colours = ["red", "green", "blue"]
    for shape in xrange(3):
      for shading in xrange(3):
        for number in xrange(3):
          for colour in xrange(3):
            offset = 80 * (shape * 27 + shading * 9 + number * 3 + colour)
            cards[(shapes[shape], shadings[shading], numbers[number], colours[colour])] = "<div class=\"realCard unselectedCard regularTau\" style=\"background-position: -%dpx 0px; display:inline-block;\"></div>" % offset
    chess_shapes = ["", "pawn", "knight", "rook"]
    astro_shapes = ["", "sun", "star", "meteors"]
    suit_shapes = ["", "club", "heart", "diamond"]
    projcards = {}
    for chess_shape in xrange(4):
      for astro_shape in xrange(4):
        for suit_shape in xrange(4):
          if not any([chess_shape, astro_shape, suit_shape]): continue
          offset = 80 * (chess_shape + astro_shape * 4 + suit_shape * 16 - 1)
          projcards[(chess_shapes[chess_shape], astro_shapes[astro_shape], suit_shapes[suit_shape])] = '<div class="realCard unselectedCard projectiveTau"  style="background-position: -%dpx 0px; display:inline-block;"></div>' % offset
    self.render(
        "about.html",
        cards=cards,
        projcards=projcards,
        )

class GoogleHandler(tornado.web.RequestHandler, tornado.auth.GoogleMixin):
  @tornado.web.asynchronous
  def get(self):
    if self.get_argument("openid.mode", None):
      self.get_authenticated_user(self.async_callback(self._on_auth))
      return
    self.authenticate_redirect()
    
  def _on_auth(self, user):
    if not user:
      raise tornado.web.HTTPError(500, "Google auth failed")
    self.set_secure_cookie("google_user", url_escape(json.dumps(user)))
    name = get_name(user['email'])
    if name is None:
      self.redirect("/choose_name")
      return
    else:
      self.set_secure_cookie('name', url_escape(name))
      self.redirect("/")

class LogoutHandler(tornado.web.RequestHandler):
  def get(self):
    self.clear_cookie("google_user")
    self.clear_cookie("name")
    self.redirect("/choose_name")

def create_application(debug):
  full_settings = dict(settings)
  #full_settings['debug'] = debug
  return tornado.web.Application([
    (r"/", MainHandler),
    # 0 players
    (r"/leaderboard/(?P<leaderboard_object>(?:players/)?)(?P<leaderboard_type>alltime|thisweek|today)/?", LeaderboardHandler),
    # 1 player
    (r"/leaderboard/(?P<leaderboard_object>(?:players/)?)(?P<leaderboard_type>alltime|thisweek|today)/(?P<slash_separated_players>[^/]+)/?", LeaderboardHandler),
    # 2+ players
    (r"/leaderboard/(?P<leaderboard_object>(?:players/)?)(?P<leaderboard_type>alltime|thisweek|today)/(?P<slash_separated_players>(?:[^/]+/){2,})(?P<conjunction>and|or)/?", LeaderboardHandler),
    (r"/graph/([^/]*)", GraphHandler),
    (r"/choose_name", ChooseNameHandler),
    (r"/new_game/(3tau|6tau|g3tau|i3tau|e3tau|4tau|3ptau|z3tau|4otau)", NewGameHandler),
    (r"/game/(\d+)", GameHandler),
    (r"/websocket/(\d*)", TauWebSocketHandler),
    (r"/gamelistwebsocket/(0|1)", GameListWebSocketHandler),
    (r"/time", TimeHandler),
    (r"/about", AboutHandler),
    (r"/google", GoogleHandler),
    (r"/logout", LogoutHandler),
  ], **full_settings)

# returns control to the main thread every timeout, where timeout is a timedelta.
def set_ping(ioloop, timeout):
  ioloop.add_timeout(timeout, lambda: set_ping(ioloop, timeout))

# cleans up games every timeout, where timeout is a timedelta.
def set_game_cleanup(ioloop, timeout):
  cleanup_games()
  ioloop.add_timeout(timeout, lambda: set_game_cleanup(ioloop, timeout))

def parse_args():
  parser = argparse.ArgumentParser(description='Run Tau server.')
  parser.add_argument('--hints', dest='hints', action='store_true',
                      help='Enable hints.')
  parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                      help='Enable debug.')
  parser.add_argument('-q', '--quick', dest='quick', action='store_true', help='Enable quick game. Deck only has 12 cards.')
  parser.add_argument('-p', '--port', dest='port', type=int, default=80, help='HTTP port.')
  parser.add_argument('-s', '--ssl_port', dest='ssl_port', type=int, default=443, help='HTTPS port.')
  return parser.parse_args()

class OptionalHTTPServer(tornado.httpserver.HTTPServer):
  def __init__(self, *args, **kwargs):
    tornado.httpserver.HTTPServer.__init__(self, *args, **kwargs)

  def _handle_connection(self, connection, address):
    if connection.getsockname()[1] == 80:
      old_ssl_options = self.ssl_options
      self.ssl_options = None
      super(tornado.httpserver.HTTPServer, self)._handle_connection(connection, address)
      self.ssl_options = old_ssl_options
    else:
      super(tornado.httpserver.HTTPServer, self)._handle_connection(connection, address)

def main():
  global args
  args = parse_args()
  application = create_application(args.debug)
  http_server = OptionalHTTPServer(application,
      ssl_options={
          "certfile" : "localhost.crt",
          "keyfile" : "localhost.key",
      })
  http_server.listen(args.port)
  http_server.listen(args.ssl_port)
  ioloop = tornado.ioloop.IOLoop.instance()
  if args.debug:
    set_ping(ioloop, datetime.timedelta(seconds=1))
  set_game_cleanup(ioloop, datetime.timedelta(seconds=GAME_CLEANUP_INTERVAL))
  ioloop.start()

if __name__ == "__main__":
  main()
  
