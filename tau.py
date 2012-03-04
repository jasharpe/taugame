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

  def on_close(self):
    sockets.remove(self)
    if self in socket_to_game.keys():
      del socket_to_game[self]
    if self in game_to_sockets[self.game_id]:
      game_to_sockets[self.game_id].remove(self)

  def send_update(self):
    game = socket_to_game[self]
    time = game.total_time if game.ended else game.get_total_time()
   
    print game.board
    print len(game.board)

    self.write_message(json.dumps({
        'type' : 'update',
        'board' : game.board,
        'scores' : game.scores,
        'time' : time,
        'ended' : game.ended
    }))

  def on_message(self, message_json):
    message = json.loads(message_json)
    print message
    if message['type'] == 'start':
      if not socket_to_game[self].started:
        socket_to_game[self].start()
      self.send_update()
    elif message['type'] == 'update':
      if socket_to_game[self].started:
        self.send_update()
    elif message['type'] == 'submit':
      game = socket_to_game[self]
      if game.started:
        game.submit_tau(map(tuple, message['cards']), self.get_cookie("name"))
        self.send_update()

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    if not self.get_cookie("name"):
      self.redirect("/choose_name")
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
  def post(self):
    if len(games.keys()) == 0:
      next_id = 0
    else:
      next_id = max(games.keys()) + 1
    games[next_id] = Game(3)
    game_to_sockets[next_id] = []
    self.redirect("/game/%d" % next_id)

class GameHandler(tornado.web.RequestHandler):
  def get(self, game_id):
    if not int(game_id) in games:
      self.redirect("/")
      return
    self.render(
        "game.html",
        game_id=game_id,
        game=games[int(game_id)])

application = tornado.web.Application([
  (r"/", MainHandler),
  (r"/choose_name", ChooseNameHandler),
  (r"/new_game", NewGameHandler),
  (r"/game/(\d*)", GameHandler),
  (r"/websocket/(\d*)", TauWebSocketHandler),
], **settings)

if __name__ == "__main__":
  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(8888)
  tornado.ioloop.IOLoop.instance().start()
