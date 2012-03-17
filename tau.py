import tornado.web
import tornado.websocket
import tornado.httpserver
from tornado import template
from tornado.escape import url_escape, url_unescape
import json
import os
from game import Game
import argparse
import datetime

settings = {
    "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
    "static_path" : os.path.join(os.path.dirname(__file__), "static"),
}

sockets = []
games = {}
socket_to_game = {}
game_to_sockets = {}
game_to_messages = {}

class TauWebSocketHandler(tornado.websocket.WebSocketHandler):
  def open(self, game_id):
    self.game_id = int(game_id)
    if not self.game_id in games:
      raise ValueError("game_id %d is bad!" % self.game_id)
    sockets.append(self)
    socket_to_game[self] = games[self.game_id]
    game_to_sockets[self.game_id].append(self)
    self.send_scores_update_to_all()
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
    print "Sending message update %s" % message
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

    hint = args.hints

    self.write_message(json.dumps({
        'type' : 'update',
        'board' : game.board,
        'scores' : self.get_scores(),
        'time' : time,
        'hint' : game.get_tau() if hint else None,
        'ended' : game.ended
    }))

  def on_message(self, message_json):
    message = json.loads(message_json)
    if message['type'] == 'start':
      if not socket_to_game[self].started:
        socket_to_game[self].start()
      self.send_update_to_all()
    elif message['type'] == 'update':
      if socket_to_game[self].started:
        self.send_update()
    elif message['type'] == 'chat':
      game_to_messages[self.game_id].append((message['name'], message['message']))
      self.send_message_update_to_all(message['name'], message['message'])
    elif message['type'] == 'submit':
      game = socket_to_game[self]
      if game.started:
        if game.submit_tau(map(tuple, message['cards']), url_unescape(self.get_cookie("name"))):
          self.send_update_to_all()

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    if not self.get_cookie("name"):
      self.redirect("/choose_name")
      return
    new_games = ("New games", filter(lambda g: not g[1].started, sorted(games.items(), None, lambda game: game[0])))
    started_games = ("Started games", filter(lambda g: g[1].started and not g[1].ended, sorted(games.items(), None, lambda game: game[0])))
    ended_games = ("Ended games", filter(lambda g: g[1].ended, sorted(games.items(), None, lambda game: game[0])))
    self.render(
        "game_list.html",
        new_games=new_games,
        started_games=started_games,
        ended_games=ended_games)

class ChooseNameHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("choose_name.html")

  def post(self):
    self.set_cookie("name", url_escape(self.get_argument("name")))
    self.redirect("/")

class NewGameHandler(tornado.web.RequestHandler):
  def post(self, type):
    if len(games.keys()) == 0:
      next_id = 0
    else:
      next_id = max(games.keys()) + 1
    games[next_id] = Game(3 if type == "3tau" else 6, args.quick)
    game_to_sockets[next_id] = []
    game_to_messages[next_id] = []
    self.redirect("/game/%d" % next_id)

class GameHandler(tornado.web.RequestHandler):
  def get(self, game_id):
    if not self.get_cookie("name") or not int(game_id) in games:
      self.redirect("/")
      return
    game = games[int(game_id)]
    self.render(
        "game.html",
        game_id=game_id,
        user_name=url_unescape(self.get_cookie("name")),
        game_type=("6 Tau" if game.size == 6 else "3 Tau"),
        game=game)

application = tornado.web.Application([
  (r"/", MainHandler),
  (r"/choose_name", ChooseNameHandler),
  (r"/new_game/(3tau|6tau)", NewGameHandler),
  (r"/game/(\d*)", GameHandler),
  (r"/websocket/(\d*)", TauWebSocketHandler),
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

if __name__ == "__main__":
  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(80)
  global args
  args = parse_args()
  ioloop = tornado.ioloop.IOLoop.instance()
  if args.debug:
    set_ping(ioloop, datetime.timedelta(seconds=1))
  ioloop.start()
