# Print interesting statistics from State records.

from collections import defaultdict
import json
import numpy as np

from state import *

# Modify these to see different stats.
name = 'jsharpe'
game_type = 'i3tau'

session = get_session()
scores = (session.query(Score)
                 .filter(Score.players.any(name=name))
                 .filter_by(num_players=1,game_type=game_type)
                 .filter(Score.invalid == False))

def num_different(cards):
  # In a tau, determine the number of properties that differ.
  ret = 0
  for i in range(4):
    ret += 3 == len(set(c[i] for c in cards))
  return ret

stats = defaultdict(lambda: [])

print 'Processing scores...'
S = 0
for score in scores:
  S += 1
  game = score.game
  prev_time = 0.
  for state in game.states:
    cur_time = state.elapsed_time
    delta = cur_time - prev_time
    prev_time = cur_time

    cards = json.loads(state.cards_json)
    stats[num_different(cards)].append(delta)

print 'All done!'
print '(There were %d scores.)' % S
print

print 'Player: %s' % name
print 'Game type: %s' % game_type
for x in sorted(stats):
  deltas = stats[x]

  print '# differing properties = %d' % x
  print '  count: %d' % len(deltas)
  # To get something meaningful from the mean, the data will need to be cleaned.
  #print '  mean: %.3lf' % np.mean(deltas)
  print '  median: %.3lf' % np.median(deltas)
  print
