import tornado.web
import tornado.websocket
import tornado.httpserver
from tornado import template
from tornado.escape import url_escape, url_unescape
import json
import os
from game import Game, InvalidGameType
import argparse
import datetime
import ssl
from state import save_game, get_all_high_scores, get_ranks, get_graph_data

settings = {
    "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
    "static_path" : os.path.join(os.path.dirname(__file__), "static"),
}

# Tau sockets
sockets = []
games = {}
socket_to_game = {}
game_to_sockets = {}
game_to_messages = {}

# game list sockets
game_list_sockets = []

def get_games(see_more_ended):
  new_games = filter(lambda g: not g[1].started, sorted(games.items(), None, lambda game: game[0]))
  started_games = filter(lambda g: g[1].started and not g[1].ended, sorted(games.items(), None, lambda game: game[0]))
  if see_more_ended:
    ended_games = filter(lambda g: g[1].ended, sorted(games.items(), None, lambda game: game[0]))
  else:
    ended_games = filter(lambda g: g[1].ended, sorted(games.items(), None, lambda game: game[0]))[-5:]
  return (new_games, started_games, ended_games)

def send_game_list_update_to_all():
  for socket in game_list_sockets:
    (new_games, started_games, ended_games) = get_games(socket.see_more_ended)
    socket.send_game_list_update(new_games, started_games, ended_games)

def get_players_in_game(game_id):
  players = set()
  for socket in game_to_sockets[game_id]:
    try:
      players.add(url_unescape(socket.get_cookie("name")))
    except:
      pass
  return sorted(players)

class GameListWebSocketHandler(tornado.websocket.WebSocketHandler):
  def open(self, see_more_ended):
    self.see_more_ended = int(see_more_ended)
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
        players.append(url_unescape(socket.get_cookie("name")))
      except:
        pass
    return players

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
    if not self.game_id in games:
      raise ValueError("game_id %d is bad!" % self.game_id)
    sockets.append(self)
    socket_to_game[self] = games[self.game_id]
    game_to_sockets[self.game_id].append(self)
    self.send_scores_update_to_all()
    send_game_list_update_to_all()
    self.write_message(json.dumps({
        'type' : 'history',
        'messages' : game_to_messages[self.game_id]
    }))

  def on_close(self):
    game = socket_to_game[self]
    
    sockets.remove(self)
    if self in socket_to_game.keys():
      del socket_to_game[self]
    if self in game_to_sockets[self.game_id]:
      game_to_sockets[self.game_id].remove(self)
    self.send_scores_update_to_all()
    send_game_list_update_to_all()

  def get_scores(self):
    game = socket_to_game[self]
    
    scores = {}
    for socket in game_to_sockets[self.game_id]:
      name = url_unescape(socket.get_cookie("name"))
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

  def send_message_update_to_all(self, name, message):
    for socket in game_to_sockets[self.game_id]:
      socket.send_message_update(name, message)

  def send_message_update(self, name, message):
    self.write_message(json.dumps({
        'type' : 'chat',
        'name' : name,
        'message' : message
    }))

  def send_update_to_all(self):
    for socket in game_to_sockets[self.game_id]:
      socket.send_update()

  def send_update(self):
    game = socket_to_game[self]
    time = game.total_time if game.ended else game.get_total_time()
    name = url_unescape(self.get_cookie("name"))

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
        numbers_map[number] = sum(times) / float(len(times))

    self.write_message(json.dumps({
        'type' : 'update',
        'board' : game.board,
        'target' : game.target_tau,
        'scores' : self.get_scores(),
        'avg_number' : numbers_map,
        'number' : len(game.get_all_taus()),
        'time' : time,
        'hint' : game.get_tau() if args.hints else None,
        'ended' : game.ended,
        'player_rank_info' : game.player_ranks[name] if game.ended and name in game.player_ranks else None
    }))

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
      game_to_messages[self.game_id].append((message['name'], message['message']))
      self.send_message_update_to_all(message['name'], message['message'])
    elif message['type'] == 'submit':
      game = socket_to_game[self]
      if game.started and not game.ended:
        if game.submit_tau(map(tuple, message['cards']), url_unescape(self.get_cookie("name"))):
          if game.ended:
            send_game_list_update_to_all()
            (db_game, score) = save_game(game)
            game.player_ranks = get_ranks(score.elapsed_time, db_game.game_type, game.scores.keys(), score.num_players)
          self.send_update_to_all()

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    see_more_ended = self.get_argument('see_more_ended', default=False)
    if not self.get_cookie("name"):
      self.redirect("/choose_name")
      return
    
    self.render(
        "game_list.html",
        see_more_ended=int(see_more_ended),
        player=url_unescape(self.get_cookie("name")))

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
  def get(self, leaderboard_type, slash_separated_players=None):
    if slash_separated_players:
      players = filter(None, slash_separated_players.split("/"))
    else:
      players = []
    all_high_scores = get_all_high_scores(10, leaderboard_type, players)
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
        time_offset=time_offset)

class ChooseNameHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("choose_name.html")

  def post(self):
    name = self.get_argument("name")
    if "/" in name:
      # TODO: put in error code
      # TODO: escape names properly generally so we don't need to outlaw slashes
      self.redirect("/choose_name")
      return
    self.set_cookie("name", url_escape(name))
    self.redirect("/")

class NewGameHandler(tornado.web.RequestHandler):
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
  }

  def get(self, game_id):
    if not self.get_cookie("name") or not int(game_id) in games:
      self.redirect("/")
      return
    game = games[int(game_id)]
    self.render(
        "game.html",
        game_id=game_id,
        user_name=url_unescape(self.get_cookie("name")),
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
            cards[(shapes[shape], shadings[shading], numbers[number], colours[colour])] = "<div class=\"realCard unselectedCard\" style=\"background-position: -%dpx 0px; display:inline-block;\"></div>" % offset
    self.render(
        "about.html",
        cards=cards
        )

application = tornado.web.Application([
  (r"/", MainHandler),
  (r"/leaderboard/(alltime|thisweek|today)/?", LeaderboardHandler),
  (r"/leaderboard/(alltime|thisweek|today)/((?:[^/]+/?)+)", LeaderboardHandler),
  (r"/graph/([^/]*)", GraphHandler),
  (r"/choose_name", ChooseNameHandler),
  (r"/new_game/(3tau|6tau|g3tau|i3tau)", NewGameHandler),
  (r"/game/(\d+)", GameHandler),
  (r"/websocket/(\d*)", TauWebSocketHandler),
  (r"/gamelistwebsocket/(0|1)", GameListWebSocketHandler),
  (r"/time", TimeHandler),
  (r"/about", AboutHandler),
], **settings)

# returns control to the main thread every 250ms
def set_ping(ioloop, timeout):
    ioloop.add_timeout(timeout, lambda: set_ping(ioloop, timeout))

def parse_args():
  parser = argparse.ArgumentParser(description='Run Tau server.')
  parser.add_argument('--hints', dest='hints', action='store_true',
                      help='Enable hints.')
  parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                      help='Enable debug.')
  parser.add_argument('-q', '--quick', dest='quick', action='store_true', help='Enable quick game. Deck only has 12 cards.')
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
  http_server = OptionalHTTPServer(application,
      ssl_options={
          "certfile" : "localhost.crt",
          "keyfile" : "localhost.key",
      })
  http_server.listen(80)
  http_server.listen(443)
  global args
  args = parse_args()
  ioloop = tornado.ioloop.IOLoop.instance()
  if args.debug:
    set_ping(ioloop, datetime.timedelta(seconds=1))
  ioloop.start()

if __name__ == "__main__":
  main()
  
