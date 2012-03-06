import tornado.web
import tornado.websocket
import tornado.httpserver
from tornado import template
import json
import os
from game import Game

settings = {
    "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
    "static_path" : os.path.join(os.path.dirname(__file__), "static"),
}

sockets = []
games = {}
socket_to_game = {}
game_to_sockets = {}

class TauWebSocketHandler(tornado.websocket.WebSocketHandler):
  def open(self, game_id):
    self.game_id = int(game_id)
    if not self.game_id in games:
      raise ValueError("game_id %d is bad!" % self.game_id)
    sockets.append(self)
    socket_to_game[self] = games[self.game_id]
    game_to_sockets[self.game_id].append(self)
    self.send_scores_update_to_all()

  def on_close(self):
    sockets.remove(self)
    if self in socket_to_game.keys():
      del socket_to_game[self]
    if self in game_to_sockets[self.game_id]:
      game_to_sockets[self.game_id].remove(self)
    self.send_scores_update_to_all()

  def send_scores_update_to_all(self):
    for socket in game_to_sockets[self.game_id]:
      socket.send_scores_update()

  def send_scores_update(self):
    game = socket_to_game[self]
    
    scores = {}
    for socket in game_to_sockets[self.game_id]:
      name = socket.get_cookie("name")
      if name in game.scores.keys():
        scores[name] = game.scores[name]
      else:
        scores[name] = []
    for (name, score) in game.scores.items():
      if not name in scores.keys():
        scores[name + " (ABSENT)"] = score
    print scores

    self.write_message(json.dumps({
        'type' : 'scores',
        'scores' : scores,
        'ended' : game.ended
    }))

  def send_update_to_all(self):
    for socket in game_to_sockets[self.game_id]:
      socket.send_update()

  def send_update(self):
    game = socket_to_game[self]
    time = game.total_time if game.ended else game.get_total_time()
   
    scores = dict(game.scores)
    for socket in game_to_sockets[self.game_id]:
      name = socket.get_cookie("name")
      if name in game.scores.keys():
        scores[name] = game.scores[name]
      else:
        scores[name] = []
    print scores

    hint = False

    self.write_message(json.dumps({
        'type' : 'update',
        'board' : game.board,
        'scores' : scores,
        'time' : time,
        'hint' : game.get_tau() if hint else None,
        'ended' : game.ended
    }))

  def on_message(self, message_json):
    message = json.loads(message_json)
    print message
    if message['type'] == 'start':
      if not socket_to_game[self].started:
        socket_to_game[self].start()
      self.send_update_to_all()
    elif message['type'] == 'update':
      if socket_to_game[self].started:
        self.send_update()
    elif message['type'] == 'submit':
      game = socket_to_game[self]
      if game.started:
        if game.submit_tau(map(tuple, message['cards']), self.get_cookie("name")):
          self.send_update_to_all()

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    if not self.get_cookie("name"):
      self.redirect("/choose_name")
      return
    self.render(
        "game_list.html",
        games=sorted(games.items(), None, lambda game: game[0]))

class ChooseNameHandler(tornado.web.RequestHandler):
  def get(self):
    self.render("choose_name.html")

  def post(self):
    self.set_cookie("name", self.get_argument("name"))
    self.redirect("/")

class NewGameHandler(tornado.web.RequestHandler):
  def post(self, type):
    print type
    if len(games.keys()) == 0:
      next_id = 0
    else:
      next_id = max(games.keys()) + 1
    games[next_id] = Game(3 if type == "3tau" else 6)
    game_to_sockets[next_id] = []
    self.redirect("/game/%d" % next_id)

class GameHandler(tornado.web.RequestHandler):
  def get(self, game_id):
    if not int(game_id) in games:
      self.redirect("/")
      return
    game = games[int(game_id)]
    self.render(
        "game.html",
        game_id=game_id,
        game_type=("6 Tau" if game.size == 6 else "3 Tau"),
        game=game)

application = tornado.web.Application([
  (r"/", MainHandler),
  (r"/choose_name", ChooseNameHandler),
  (r"/new_game/(3tau|6tau)", NewGameHandler),
  (r"/game/(\d*)", GameHandler),
  (r"/websocket/(\d*)", TauWebSocketHandler),
], **settings)

if __name__ == "__main__":
  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(80)
  tornado.ioloop.IOLoop.instance().start()
