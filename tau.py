# -- coding: utf-8 --

import tornado.web
import tornado.auth
import tornado.websocket
import tornado.httpserver
from tornado.escape import url_escape, url_unescape, xhtml_escape, xhtml_unescape
import json
import os
import re
from game import Game, InvalidGameType
from lobby import Lobby, InvalidGameId
import argparse
import datetime, time
import ssl
from state import save_game, get_all_high_scores, get_all_high_games, get_ranks, get_rank, get_graph_data, check_name, set_name, get_name, get_score
from secrets import cookie_secret
from constants import GAME_TYPE_INFO
from preset_decks import PRESET_TAUS
import fingeo

# The time in seconds that games should be allowed to live without activity
# before they are eligible to be hidden if they contain no players.
GAME_EXPIRY = 1200

# The number of seconds between game cleanup sweeps.
GAME_CLEANUP_INTERVAL = 600

SETTINGS = {
    "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
    "static_path" : os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret" : cookie_secret,
}

lobby = Lobby(GAME_EXPIRY)

class GameListWebSocketHandler(tornado.websocket.WebSocketHandler):
  def open(self, see_more_ended):
    self.see_more_ended = int(see_more_ended)
    self.lobby = lobby
    self.name = url_unescape(self.get_secure_cookie("name"))
    self.lobby.open_game_list_socket(self)
  
  def on_close(self):
    self.lobby.close_game_list_socket(self)

  def on_message(self, message_json):
    message = json.loads(message_json)
    if message['type'] == 'update':
      self.lobby.update_game_list_socket(self, self.see_more_ended)

  def send_player_list_update(self, players):
    self.write_message(json.dumps({
        'type' : 'players',
        'players' : [xhtml_escape(player) for player in players]
    }))

  def transform_games(self, games):
    return [{
      'id' : game.id,
      'size' : game.game.size,
      'type' : game.game.type,
      'training' : game.training,
      'players' : [xhtml_escape(player) for player in self.lobby.get_players_in_game(game.id)],
    } for game in games]

  def send_game_list_update(self, new_games, started_games, ended_games):
    self.write_message(json.dumps({
        'type' : 'games',
        'new_games' : self.transform_games(new_games),
        'started_games' : self.transform_games(started_games),
        'ended_games' : self.transform_games(ended_games)
    }))

class TauWebSocketHandler(tornado.websocket.WebSocketHandler):
  def open(self, game_id):
    self.opened = False

    game_id = int(game_id)
    self.name = url_unescape(self.get_secure_cookie("name"))
    try:
      self.game = lobby.game_id_to_game[game_id]
    except KeyError:
      self.close()
      return

    self.game.open_game_socket(self)
    self.opened = True

  def on_close(self):
    if self.opened:
      self.game.close_game_socket(self)

  def escape_message(self, message, message_type):
    if not message_type in ["new_game"]:
      return xhtml_escape(message)
    else:
      return message

  def send_history_update(self, messages):
    self.write_message(json.dumps({
        'type' : 'history',
        'messages' : [(xhtml_escape(name), self.escape_message(message, message_type), message_type) for (name, message, message_type) in messages]
    }))

  def send_scores_update(self, scores, ended, is_pausable):
    self.write_message(json.dumps({
        'type' : 'scores',
        'scores' : scores,
        'ended' : ended,
        'is_pausable' : is_pausable,
    }))

  def send_message_update(self, name, message, message_type):
    self.write_message(json.dumps({
        'type' : 'chat',
        'name' : xhtml_escape(name),
        'message' : self.escape_message(message, message_type),
        'message_type' : message_type,
    }))

  def send_update(self, board, all_taus, all_stale_taus, paused, target, wrong_property, scores, avg_number, number, time, hint, ended, player_rank_info, found_puzzle_taus, training_options, is_pausable):
    self.write_message(json.dumps({
        'type' : 'update',
        'board' : board,
        'all_taus' : all_taus,
        'all_stale_taus' : all_stale_taus,
        'paused' : paused,
        'target' : target,
        'wrong_property' : wrong_property,
        'scores' : scores,
        'avg_number' : avg_number,
        'number' : number,
        'time' : time,
        'hint' : hint if args.hints or self.game.training else None,
        'ended' : ended,
        'player_rank_info' : player_rank_info,
        # puzzle mode
        'found_puzzle_taus' : found_puzzle_taus,
        'training_options' : training_options,
        'is_pausable' : is_pausable,
    }))

  def send_old_found_puzzle_tau_index(self, index):
    self.write_message(json.dumps({
        'type' : 'old_found_puzzle_tau',
        'index' : index,
    }))

  def send_training_options(self, training_options):
    self.write_message(json.dumps({
      'type' : 'training_options',
      'options' : training_options,
    }))

  def on_message(self, message_json):
    message = json.loads(message_json)
    if message['type'] == 'start':
      self.game.start_game()
    elif message['type'] == 'update':
      self.game.request_update(self)
    elif message['type'] == 'chat':
      self.game.add_chat(xhtml_unescape(message['name']), message['message'], "chat")
    elif message['type'] == 'pause':
      self.game.pause(message['pause'])
    elif message['type'] == 'submit':
      self.game.submit_tau(self, message['cards'])
    elif message['type'] == 'training_option':
      self.game.set_training_option(message['option'], message['value'])

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
        player=url_unescape(self.get_secure_cookie("name")),
        game_type_info=GAME_TYPE_INFO)

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
    if leaderboard_object in ["", "players/"]:
      unique_players = leaderboard_object == "players/"
      all_high_scores = get_all_high_scores(10, leaderboard_type, players, conjunction, unique_players=unique_players)
    elif leaderboard_object in ["games/"]:
      all_high_scores = get_all_high_games(10, leaderboard_type, players, conjunction)

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
        leaderboard_object=leaderboard_object,
        time_offset=time_offset,
        conjunction=conjunction,
        game_type_info=GAME_TYPE_INFO)

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

  def is_valid_name(self, name):
    end_chars = 'a-zA-Z0-9!@#$%^&*()\\-_+={}\\[\\]|:;"\'<>,.?~`'
    middle_only_chars = ' '
    regex = '^[' + end_chars + '](([' + end_chars + middle_only_chars + '])*[' + end_chars + '])?$'
    chars_allowed = re.compile(regex)
    return bool(chars_allowed.match(name))

  def post(self):
    name = self.get_argument("name")
    if not self.is_valid_name(name):
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
    try:
      parent = int(self.get_argument("parent"))
    except:
      parent = None

    try:
      training = self.get_argument("training") == "true"
    except:
      training = False

    name = url_unescape(self.get_secure_cookie("name"))

    try:
      game = lobby.new_game(type, name, parent, args.quick, args.use_preset_decks, training)
    except InvalidGameType:
      self.redirect('/')
      return
    
    self.redirect("/game/%d" % game.id)
    return

class GameHandler(tornado.web.RequestHandler):
  game_type_to_type_string_map = dict(GAME_TYPE_INFO)

  @require_name
  def get(self, game_id):
    try:
      game = lobby.get_game(int(game_id))
    except InvalidGameId:
      self.redirect("/?invalid_game_id_error=1")
      return
    self.render(
        "game.html",
        game_id=game_id,
        user_name=url_unescape(self.get_secure_cookie("name")),
        game_type=self.game_type_to_type_string_map[game.game.type],
        debug=int(self.get_argument('debug', default=0)),
        game=game.game,
        game_type_info=GAME_TYPE_INFO,
        training=game.training)

class TimeHandler(tornado.web.RequestHandler):
  def post(self):
    new_time_offset = url_escape(self.get_argument("time_offset"))
    self.set_cookie("time_offset", new_time_offset)

def get_wrong_property(space, cards):
  s = space.sum_cards(cards)
  for (i, val) in enumerate(s):
    if val != 0:
      return i
  return -1

class RecapHandler(tornado.web.RequestHandler):
  def get(self, score_id):
    score = get_score(score_id)
    if score is None:
      raise tornado.web.HTTPError(404)

    try:
      time_offset = int(url_unescape(self.get_cookie("time_offset")))
    except:
      time_offset = 0

    try:
      deck = list(reversed(map(tuple, score.game.deck)))
    except:
      deck = []
    need_deck = not deck
    taus = []
    num_taus = []
    tau_times = []
    targets = []
    wrong_properties = []
    players = []
    total_elapsed_time = 0
    for state in score.game.states:
      players.append(state.player.name)
      tau_times.append(state.elapsed_time - total_elapsed_time)
      total_elapsed_time = state.elapsed_time
      space = fingeo.get_space(score.game_type)
      target = space.sum_cards(state.cards)
      targets.append(target)
      wrong_property = get_wrong_property(space, state.cards)
      wrong_properties.append(wrong_property)
      taus.append(state.cards)
      game = Game(score.game_type, deck=reversed(filter(None, state.board)), targets=[target], wrong_properties=[wrong_property])
      num_taus.append(game.count_taus())
      if need_deck:
        for card in state.board:
          if card and not tuple(card) in deck:
            deck.append(tuple(card))

    (percentile, rank) = get_rank(score.elapsed_time, "alltime", score.num_players, score.game_type, "all", "exact", None)

    self.render(
        "recap.html",
        players=map(lambda x: x.name, score.players),
        num_taus=zip(map(lambda x: "%.2f" % (x), tau_times), map(str, num_taus), players),
        avg_taus=sum(num_taus)/float(len(num_taus)),
        score=score,
        time_offset=time_offset,
        game_type_info=dict(GAME_TYPE_INFO),
        percentile=percentile,
        rank=rank)

class SettingsHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("settings.html")

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
      if not self.get_secure_cookie("name"):
        self.redirect("/choose_name")
        return
      try:
        set_name(user['email'], self.get_secure_cookie("name"))
        self.redirect("/")
      except:
        self.clear_cookie('name')
        self.redirect("/choose_name")
      return
    
    self.set_secure_cookie('name', url_escape(name))
    self.redirect("/")

class LogoutHandler(tornado.web.RequestHandler):
  def get(self):
    self.clear_cookie("google_user")
    self.clear_cookie("name")
    self.redirect("/choose_name")

class TestFrameHandler(tornado.web.RequestHandler):
  @require_name
  def get(self, specified_game_type):
    if not args.debug:
      raise tornado.web.HTTPError(404)

    game_type_to_taus = {}
    for (game_type, taus) in PRESET_TAUS.items():
      space = fingeo.get_space(game_type)
      game_type_to_taus[game_type] = map(lambda tau: map(lambda card: space.to_client_card(card), tau), PRESET_TAUS[game_type])

    self.render(
        "testframe.html",
        game_type=specified_game_type,
        game_type_to_taus=game_type_to_taus,
    )

def create_application(debug):
  full_settings = dict(SETTINGS)
  handlers = [
    (r"/", MainHandler),
    # 0 players
    (r"/leaderboard/(?P<leaderboard_object>(?:(?:players|games)/)?)(?P<leaderboard_type>alltime|thisweek|today)/?", LeaderboardHandler),
    # 1 player
    (r"/leaderboard/(?P<leaderboard_object>(?:(?:players|games)/)?)(?P<leaderboard_type>alltime|thisweek|today)/(?P<slash_separated_players>[^/]+)/?", LeaderboardHandler),
    # 2+ players
    (r"/leaderboard/(?P<leaderboard_object>(?:(?:players|games)/)?)(?P<leaderboard_type>alltime|thisweek|today)/(?P<slash_separated_players>(?:[^/]+/){2,})(?P<conjunction>and|or)/?", LeaderboardHandler),
    (r"/graph/([^/]*)", GraphHandler),
    (r"/choose_name", ChooseNameHandler),
    (r"/new_game/(3tau|6tau|g3tau|i3tau|m3tau|e3tau|4tau|3ptau|z3tau|4otau|n3tau|bqtau|sbqtau)", NewGameHandler),
    (r"/game/(\d+)", GameHandler),
    (r"/recap/(\d+)", RecapHandler),
    (r"/websocket/(\d*)", TauWebSocketHandler),
    (r"/gamelistwebsocket/(0|1)", GameListWebSocketHandler),
    (r"/time", TimeHandler),
    (r"/settings", SettingsHandler),
    (r"/about", AboutHandler),
    (r"/google", GoogleHandler),
    (r"/logout", LogoutHandler),
  ]
  if debug:
    handlers.append((r"/testframe/(all|3tau|6tau|g3tau|i3tau|m3tau|e3tau|4tau|3ptau|z3tau|4otau|n3tau|bqtau|sbqtau)", TestFrameHandler))
  return tornado.web.Application(handlers, **full_settings)

# returns control to the main thread every timeout, where timeout is a timedelta.
def set_ping(ioloop, timeout):
  ioloop.add_timeout(timeout, lambda: set_ping(ioloop, timeout))

# cleans up games every timeout, where timeout is a timedelta.
def set_game_cleanup(ioloop, timeout):
  lobby.cleanup_games()
  ioloop.add_timeout(timeout, lambda: set_game_cleanup(ioloop, timeout))

def parse_args():
  parser = argparse.ArgumentParser(description='Run Tau server.')
  parser.add_argument('--hints', dest='hints', action='store_true',
                      help='Enable hints.')
  parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                      help='Enable debug.')
  parser.add_argument('-q', '--quick', dest='quick', action='store_true', help='Enable quick game. Deck only has 12 cards.')
  parser.add_argument('-r', '--preset', dest='use_preset_decks', action='store_true', help='Enable preset decks. Each game type will always use the same deck.')
  parser.add_argument('-p', '--port', dest='port', type=int, default=80, help='HTTP port.')
  parser.add_argument('-s', '--ssl_port', dest='ssl_port', type=int, default=443, help='HTTPS port.')
  return parser.parse_args()

class OptionalHTTPServer(tornado.httpserver.HTTPServer):
  def __init__(self, port, *args, **kwargs):
    self.port = port
    tornado.httpserver.HTTPServer.__init__(self, *args, **kwargs)

  def _handle_connection(self, connection, address):
    if connection.getsockname()[1] == self.port:
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
  http_server = OptionalHTTPServer(args.port, application,
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
  
