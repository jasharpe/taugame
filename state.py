from db import Base, get_session
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Table, Boolean, distinct, func, or_, and_
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import desc, asc
import datetime
import json
import logging
import itertools
from game import game_types
from collections import defaultdict

CLOSE_THRESHOLD = 5.0

# recursive defaultdict
def rdefaultdict(): return defaultdict(rdefaultdict)

def get_score(score_id):
  session = get_session()
  try:
    return session.query(Score).filter_by(id=score_id).first()
  except:
    return None

def get_graph_data(player):
  session = get_session()
  ret = {}
  for game_type in game_types:
    time_limit = (600 if game_type == '3tau' else 2700)
    raw_data = session.query(Score).filter(Score.elapsed_time < time_limit).filter(Score.date > datetime.datetime(year=2012, month=1, day=2)).filter(Score.players.any(name=player)).filter_by(num_players=1,game_type=game_type).filter(Score.invalid == False).order_by(asc(Score.date))
    ret[game_type] = raw_data
  return ret

filter_map = {
    "alltime" : lambda: Score.date >= datetime.datetime.min,
    "thisweek" : lambda: Score.date >= datetime.datetime.now() - datetime.timedelta(days=7),
    "today" : lambda: Score.date >= datetime.datetime.now() - datetime.timedelta(days=1),
}

def filter_for_players(players, query):
  return query.join((DBPlayer, Score.players)).filter(or_(*[DBPlayer.name == player for player in players]))

def base_score_query(leaderboard_type, query):
  time_filter = filter_map[leaderboard_type]()
  return query.filter(time_filter).filter(Score.invalid == False)

def get_numbers(leaderboard_type, players):
  session = get_session()
  numbers_query = base_score_query(leaderboard_type, session.query(distinct(Score.num_players), Score.game_type))
  if players:
    numbers_query = filter_for_players(players, numbers_query)
  return list(numbers_query)

def leaderboard_query(num_players, game_type, query):
  return query.filter_by(num_players=num_players,game_type=game_type)

def simple_query(leaderboard_type, num_players, game_type, query):
  return leaderboard_query(num_players, game_type, base_score_query(leaderboard_type, query))

def and_query(players, query):
  return query.group_by(Score.id).having(func.count(distinct(DBPlayer.name)) == len(players))

def num_better_than_query(elapsed_time, query):
  return query.filter(Score.elapsed_time < elapsed_time).count()

def get_all_high_scores(num_scores, leaderboard_type, players, conjunction, unique_players=False):
  session = get_session()
  ret = defaultdict(dict)
  for (number, game_type) in get_numbers(leaderboard_type, players):
    top_scores = simple_query(leaderboard_type, number, game_type, session.query(Score)).order_by(asc(Score.elapsed_time))
    if players:
      top_scores = filter_for_players(players, top_scores)
    if conjunction == "and":
      top_scores = and_query(players, top_scores)
        
    if unique_players:
      q = simple_query(leaderboard_type, number, game_type, session.query(Score.team_id, func.min(Score.elapsed_time).label('min_elapsed_time'))).group_by(Score.team_id).subquery()
      top_scores = top_scores.join(q, Score.team_id == q.c.team_id)
      top_scores = top_scores.filter(Score.elapsed_time == q.c.min_elapsed_time)
    scores = list(top_scores.limit(num_scores))
    if scores:
      ret[game_type][number] = scores
  return ret

def get_all_high_games(num_results, leaderboard_type, players, conjunction):
  session = get_session()
  ret = defaultdict(dict)
  for (number, game_type) in get_numbers(leaderboard_type, players):
    query = simple_query(leaderboard_type, number, game_type, session.query(Score)).filter(Score.elapsed_time < 3600)
    if players:
      query = filter_for_players(players, query).group_by(Score.id)
    if conjunction == "and":
      query = and_query(players, query)
    results = list(query.from_self(Score, func.count().label("num_games"), func.sum(Score.elapsed_time)).group_by(Score.team_id).order_by('num_games desc').limit(num_results))
    if results:
      ret[game_type][number] = results
  return ret

def get_or_create_dbplayer(session, name):
  player = session.query(DBPlayer).filter_by(name=name).first()
  if player:
    return player
  else:
    player = DBPlayer(name)
    session.add(player)
    return player

# players is a list of DBPlayers
def get_or_create_team(session, players):
  team = session.query(Team).join((DBPlayer, Team.players)).filter(or_(*[DBPlayer.id == player.id for player in players])).group_by(Team.id).having(func.count(distinct(DBPlayer.id)) == len(players)).first()
  if team:
    return team
  else:
    team = Team(players)
    session.add(team)
    return team

def get_percentile(total, better):
  if total == 0:
    percentile = 0
  elif better == 0:
    percentile = 100
  else:
    percentile = round(100 * ((total - better) / float(total)))
    if percentile == 100:
      percentile = 99
  return percentile

def get_rank(elapsed_time, leaderboard_type, num_players, game_type, leaderboard, close, player_name):
  session = get_session()

  num_better_scores = simple_query(leaderboard_type, num_players, game_type, session.query(Score))
  if leaderboard != "all":
    num_better_scores = simple_query(leaderboard_type, num_players, game_type, session.query(Score)).join((DBPlayer, Score.players)).filter(DBPlayer.name == player_name)
  if close == "close":
    better = num_better_than_query(elapsed_time - CLOSE_THRESHOLD, num_better_scores)
  else:
    better = num_better_than_query(elapsed_time, num_better_scores)
  
  percentile = get_percentile(num_better_scores.count(), better)

  return (percentile, better + 1)

def get_ranks(total_time, game_type, player_names, num_players):
  import time
  init_time = time.time()

  global_ranks = rdefaultdict()
  global_ranks["close"]["personal"] = None
  global_ranks["exact"]["personal"] = None

  player_ranks = rdefaultdict()

  arguments = [
    player_names,
    ["close", "exact"],
    ["personal", "all"],
    ["alltime", "thisweek", "today"]
  ]

  for (player_name, close, leaderboard, leaderboard_type) in itertools.product(*arguments):
    (percentile, rank) = get_rank(total_time, leaderboard_type, num_players, game_type, leaderboard, close, player_name)
    rank_object = { 'percentile' : percentile, 'rank' : rank }          
    player_ranks[player_name][close][leaderboard][leaderboard_type] = rank_object
    if leaderboard == "all":
      global_ranks[close][leaderboard][leaderboard_type] = rank_object
  
  if time.time() - init_time > 0.5:
    logging.warning("Took %.03f seconds to fetch player ranks for %d player", time.time() - init_time, num_players)

  return {
      'global' : global_ranks,
      'players' : player_ranks
  }

def save_game(game, training):
  session = get_session()
  db_game = DBGame(game.type)
  name_to_player_map = {}
  player_to_score_map = {}
  last_elapsed_time = 0
  for (board, tau) in zip(game.boards, game.taus):
    (elapsed_time, total_taus, player, cards) = tau
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
  players = name_to_player_map.values()
  team = get_or_create_team(session, players)
  score = Score(last_elapsed_time, datetime.datetime.utcnow(), db_game, players, team, player_to_score_map)
  if training:
    score.invalid = True
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

team_players = Table("team_players", Base.metadata,
    Column('team_id', Integer, ForeignKey('teams.id')),
    Column('player_id', Integer, ForeignKey('players.id')))

class DBPlayer(Base):
  __tablename__ = 'players'

  id = Column(Integer, primary_key=True)
  name = Column(String)

  scores = relationship('Score', secondary=score_players, backref='players')
  teams = relationship('Team', secondary=team_players, backref='players')

  def __init__(self, name):
    self.name = name

  def __repr__(self):
    return "<DBPlayer('%s')>" % (self.name)

class Team(Base):
  __tablename__ = 'teams'

  id = Column(Integer, primary_key=True)

  def __init__(self, players):
    self.players = players

class Score(Base):
  __tablename__ = 'scores'

  id = Column(Integer, primary_key=True)
  elapsed_time = Column(Float)
  num_players = Column(Integer)
  game_id = Column(Integer, ForeignKey('games.id'))
  game = relationship("DBGame", uselist=False, backref=backref('score'))
  team_id = Column(Integer, ForeignKey('teams.id'))
  team = relationship("Team", backref=backref('scores'))
  game_type = Column(String)
  date = Column(DateTime)
  player_scores_json = Column(String)
  invalid = Column(Boolean)

  def __init__(self, elapsed_time, date, game, players, team, player_scores):
    self.elapsed_time = elapsed_time
    self.date = date
    self.game = game
    self.team = team
    self.players = players
    self.num_players = len(players)
    self.game_type = game.game_type
    self.player_scores_json = json.dumps(player_scores)
    self.invalid = False

  def __repr__(self):
    return "<Score(%f, %s, %s, %s, %s)>" % (self.elapsed_time, repr(self.date), self.game, self.players, repr(self.player_scores()))

  def player_scores(self):
    return json.loads(self.player_scores_json)

# Returns true if the name is allowed to be taken.
def check_name(name, email=None):
  session = get_session()
  names = session.query(Name).filter_by(name=name)
  if list(names):
    user_name = names[0]
    return user_name.email == email
  return True

def get_name(email):
  session = get_session()
  existing_names = session.query(Name).filter_by(email=email)
  if list(existing_names):
    return existing_names[0].name
  return None

def set_name(email, name):
  session = get_session()
  if not check_name(name, email):
    raise Exception("name %s is taken")
  existing_names = session.query(Name).filter_by(email=email)
  if list(existing_names):
    existing_name = existing_names[0]
    existing_name.name = name
    session.add(existing_name)
    session.commit()
  else:
    new_name = Name(email, name)
    session.add(new_name)
    session.commit()

class Name(Base):
  __tablename__ = 'names'

  id = Column(Integer, primary_key=True)
  email = Column(String, unique=True)
  name = Column(String, unique=True)

  def __init__(self, email, name):
    self.email = email
    self.name = name

  def __repr__(self):
    return "<Name(%s, %s)>" % (email, name)

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
    return json.loads(self.board_json)

  def cards(self):
    return json.loads(self.cards_json)
