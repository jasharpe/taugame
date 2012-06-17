from db import Base, get_session
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Table, distinct, func, or_
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import desc, asc
import datetime
import json
import logging
from game import game_types

CLOSE_THRESHOLD = 5.0

def get_graph_data(player):
  logging.warning("get_graph_data(%s)", player)

  session = get_session()
  ret = {}
  for game_type in game_types:
    time_limit = (600 if game_type == '3tau' else 2700)
    raw_data = session.query(Score).filter(Score.elapsed_time < time_limit).filter(Score.date > datetime.datetime(year=2012, month=1, day=2)).filter(Score.players.any(name=player)).filter_by(num_players=1,game_type=game_type).order_by(asc(Score.date))
    ret[game_type] = raw_data
  return ret

filter_map = {
    "alltime" : lambda: Score.date >= datetime.datetime.min,
    "thisweek" : lambda: Score.date >= datetime.datetime.now() - datetime.timedelta(days=7),
    "today" : lambda: Score.date >= datetime.datetime.now() - datetime.timedelta(days=1),
}

def get_numbers(leaderboard_type, player):
  session = get_session()
  time_filter = filter_map[leaderboard_type]()
  numbers_query = session.query(distinct(Score.num_players), Score.game_type).filter(time_filter)
  if player is not None:
    numbers_query = numbers_query.filter(Score.players.any(name=player))
  return list(numbers_query)

def get_all_high_scores(num_scores, leaderboard_type, player):
  session = get_session()
  time_filter = filter_map[leaderboard_type]()
  ret = {}
  for (number, game_type) in get_numbers(leaderboard_type, player):
    if not game_type in ret:
      ret[game_type] = {}
    top_scores = session.query(Score).filter_by(num_players=number,game_type=game_type).filter(time_filter).order_by(asc(Score.elapsed_time))
    if player is not None:
      top_scores = top_scores.filter(Score.players.any(name=player))
    ret[game_type][number] = list(top_scores.limit(num_scores))
  return ret

def get_or_create_dbplayer(session, name):
  player = session.query(DBPlayer).filter_by(name=name).first()
  if player:
    return player
  else:
    player = DBPlayer(name)
    session.add(player)
    return player

def new_get_ranks(total_time, game_type, player_names, num_players):
  import time
  init_time = time.time()

  session = get_session()
  all_scores = session.query(Score).filter_by(num_players=num_players).filter(Score.game_type == game_type)
  #player_expressions = []
  #for player_name in player_names:
  #  player_expressions.append(Score.players.any(name=player_name))
  #all_scores = all_scores.filter(or_(*player_expressions))
  all_scores = list(all_scores)
  logging.warning("Took %.03f seconds to query player ranks for %d player", time.time() - init_time, num_players)

  dates = {
      "alltime" : datetime.datetime.min,
      "thisweek" : datetime.datetime.now() - datetime.timedelta(days=7),
      "today" : datetime.datetime.now() - datetime.timedelta(days=1),
  }

  ret = {}
  all_cache = {}
  for player_name in player_names:
    ret[player_name] = {}
    for close in ["close", "exact"]:
      time_threshold = total_time - (CLOSE_THRESHOLD if close == "close" else 0)
      elapsed_time_constraint = lambda score: score.elapsed_time < time_threshold
      ret[player_name][close] = {}
      for leaderboard in ["personal", "all"]:
        def leaderboard_constraint(score):
          if leaderboard_constraint == "all":
            return True
          else:
            player_names = set(map(lambda p: p.name, score.players))
            return player_name in player_names
        ret[player_name][close][leaderboard] = {}
        for leaderboard_type in ["alltime", "thisweek", "today"]:
          key = (close, leaderboard, leaderboard_type)
          if key in all_cache:
            ret[player_name][close][leaderboard][leaderboard_type] = all_cache[key]
            continue
          date_constraint = lambda score: score.date >= dates[leaderboard_type]
          def constraints(score):
            return all([date_constraint(score), leaderboard_constraint(score)])

          filtered_scores = filter(constraints, all_scores)
          filtered_by_time_scores = filter(elapsed_time_constraint, filtered_scores)

          if len(filtered_scores) == 0:
            percentile = 0
          elif len(filtered_by_time_scores) == len(filtered_scores):
            percentile = 100
          else:
            percentile = round(100 * ((len(filtered_scores) - len(filtered_by_time_scores)) / float(len(filtered_scores))))
            if percentile == 100:
              percentile = 99
            
          ret[player_name][close][leaderboard][leaderboard_type] = {
              'percentile' : "%d" % percentile,
              'rank' : len(filtered_by_time_scores) + 1,
          }
          #if leaderboard == "all":
            #all_cache[key] = ret[player_name][close][leaderboard][leaderboard_type]
  logging.warning("Took %.03f seconds to process player ranks for %d player", time.time() - init_time, num_players)

  return ret

def get_ranks(total_time, game_type, player_names, num_players):
  import time
  init_time = time.time()

  ret = {}
  session = get_session()
  for player_name in player_names:
    ret[player_name] = {}
    for close in ["close", "exact"]:
      ret[player_name][close] = {}
      for leaderboard in ["personal", "all"]:
        ret[player_name][close][leaderboard] = {}
        for leaderboard_type in ["alltime", "thisweek", "today"]:
          time_filter = filter_map[leaderboard_type]()
          elapsed_time_filter = Score.elapsed_time < total_time - (CLOSE_THRESHOLD if close == "close" else 0)
          if leaderboard == "all":
            num_better_scores = session.query(Score).filter(time_filter).filter(Score.game_type == game_type).filter(Score.num_players == num_players)
          else:
            num_better_scores = session.query(Score).join((DBPlayer, Score.players)).filter(time_filter).filter(Score.game_type == game_type).filter(Score.num_players == num_players).filter(DBPlayer.name == player_name)
          total = num_better_scores.count()
          better = num_better_scores.filter(elapsed_time_filter).count()
          if total == 0:
            percentile = 0
          elif better == 0:
            percentile = 100
          else:
            percentile = round(100 * ((total - better) / float(total)))
            if percentile == 100:
              percentile = 99
          
          ret[player_name][close][leaderboard][leaderboard_type] = {
              'percentile' : percentile,
              'rank' : better + 1,
          }
  logging.warning("Took %.03f seconds to fetch player ranks for %d player", time.time() - init_time, num_players)

  return ret

def save_game(game):
  session = get_session()
  db_game = DBGame(game.type)
  name_to_player_map = {}
  player_to_score_map = {}
  last_elapsed_time = 0
  for (board, tau) in zip(game.boards, game.taus):
    (elapsed_time, total_taus, player, cards) = tau
    if player == "dummy":
      continue
    if player in name_to_player_map:
      db_player = name_to_player_map[player]
      player_to_score_map[player] += 1
    else:
      db_player = get_or_create_dbplayer(session, player)
      player_to_score_map[player] = 1
    name_to_player_map[db_player.name] = db_player

    state = State(elapsed_time, board, cards, db_player)
    db_game.states.append(state)
    last_elapsed_time = elapsed_time
  score = Score(last_elapsed_time, datetime.datetime.utcnow(), db_game, name_to_player_map.values(), player_to_score_map)
  session.add(score)
  session.add(db_game)
  session.commit()
  return (db_game, score)

class DBGame(Base):
  __tablename__ = 'games'

  id = Column(Integer, primary_key=True)
  game_type = Column(String)

  def __init__(self, game_type):
    self.game_type = game_type

  def __repr__(self):
    return "<DBGame('%s')>" % (self.game_type)

score_players = Table("score_players", Base.metadata,
    Column('score_id', Integer, ForeignKey('scores.id')),
    Column('player_id', Integer, ForeignKey('players.id')))

class DBPlayer(Base):
  __tablename__ = 'players'

  id = Column(Integer, primary_key=True)
  name = Column(String)

  scores = relationship('Score', secondary=score_players, backref='players')

  def __init__(self, name):
    self.name = name

  def __repr__(self):
    return "<DBPlayer('%s')>" % (self.name)

class Score(Base):
  __tablename__ = 'scores'

  id = Column(Integer, primary_key=True)
  elapsed_time = Column(Float)
  num_players = Column(Integer)
  game_id = Column(Integer, ForeignKey('games.id'))
  game = relationship("DBGame", uselist=False, backref=backref('score'))
  game_type = Column(String)
  date = Column(DateTime)
  player_scores_json = Column(String)

  def __init__(self, elapsed_time, date, game, players, player_scores):
    self.elapsed_time = elapsed_time
    self.date = date
    self.game = game
    self.players = players
    self.num_players = len(players)
    self.game_type = game.game_type
    self.player_scores_json = json.dumps(player_scores)

  def __repr__(self):
    return "<Score(%f, %s, %s, %s, %s)>" % (self.elapsed_time, repr(self.date), self.game, self.players, repr(self.player_scores()))

  def player_scores(self):
    return json.loads(self.player_scores_json)

# Represents the state just before a tau is taken, and
# the tau that was taken.
class State(Base):
  __tablename__ = 'states'

  id = Column(Integer, primary_key=True)
  elapsed_time = Column(Float)
  board_json = Column(String)
  cards_json = Column(String)

  # foreign keys
  game_id = Column(Integer, ForeignKey('games.id'))
  game = relationship("DBGame", backref=backref('states'))
  player_id = Column(Integer, ForeignKey('players.id'))
  player = relationship("DBPlayer")

  def __init__(self, elapsed_time, board, cards, player):
    self.elapsed_time = elapsed_time
    self.board_json = json.dumps(board)
    self.cards_json = json.dumps(cards)
    self.player = player

  def board(self):
    return json.loads(board_json)

  def cards(self):
    return json.loads(cards_json)
